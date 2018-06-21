# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions
from dateutil import parser
import re
import html2text
try:
    from markdown import markdown
except:
    pass


class JiraIssue(models.Model):

    _inherit = 'project.task'

    def create_jira_dict(self, vals, type):
        jira_dict = dict(
            fields=dict()
        )

        if 'project_id' in vals:
            if type == 'WRITE':
                raise exceptions.Warning('You can not move Issue to another Project via Rest Api.')
            jira_dict['fields']['project'] = dict(id=self.env['project.project'].browse(vals['project_id']).jira_id)
        if 'name' in vals:
            jira_dict['fields']['summary'] = vals['name']
        if 'issue_type_id' in vals:
            jira_dict['fields']['issuetype'] = dict(id=self.env['jira.issue.type'].browse(vals['issue_type_id']).jira_id)
        if 'description' in vals:
            jira_dict['fields']['description'] = html2text.html2text(vals['description'])
        if 'user_id' in vals:
            jira_dict['fields']['assignee'] = dict(name=self.env['res.users'].browse(vals['user_id']).jira_id)
        if 'reporter_id' in vals:
            jira_dict['fields']['reporter'] = dict(name=self.env['res.users'].browse(vals['reporter_id']).jira_id)
        if 'priority_id' in vals:
            jira_dict['fields']['priority'] = dict(id=self.env['jira.issue.priority'].browse(vals['priority_id']).jira_id)
        if 'tag_ids' in vals:
            tag_list = list()
            for t in self.tag_ids:
                tag_list.append(t.name)
            jira_dict['fields']['labels'] = tag_list
        if 'version_ids' in vals:
            jira_dict['fields']['versions'] = list()
            for v in self.version_ids:
                jira_dict['fields']['versions'].append(dict(id=v.jira_id))
            if type == 'CREATE' and not self.version_ids:
                jira_dict['fields'].pop('versions')
        if 'fix_version_ids' in vals and vals['fix_version_ids']:
            jira_dict['fields']['fixVersions'] = list()
            for v in self.fix_version_ids:
                jira_dict['fields']['fixVersions'].append(dict(id=v.jira_id))
        if 'date_deadline' in vals:
            jira_dict['fields']['duedate'] = vals['date_deadline'] or None
            if type == 'CREATE' and not jira_dict['fields']['duedate']:
                jira_dict['fields'].pop('duedate')
        if 'component_ids' in vals:
            jira_dict['fields']['components'] = list()
            for c in self.component_ids:
                jira_dict['fields']['components'].append(dict(id=c.jira_id))
        if 'epic_id' in vals:
            epic_id = None
            if vals['epic_id']:
                epic_id = self.env['project.task'].browse(vals['epic_id']).key
            jira_dict['fields'][self.env['jira.field'].jira_key('Epic Link').jira_id] = epic_id
        if self.issue_type_id.name == 'Epic':
            if 'name' in vals or 'issue_type_id' in vals:
                jira_dict['fields'][self.env['jira.field'].jira_key('Epic Name').jira_id] = self.name

        if 'sprint_ids' in vals and type == 'WRITE':
            for s in self.sprint_ids:
                data_dict = dict(issues=[self.key])
                self.env.ref('jira_connector.jira_settings_record').post('sprint/' + s.jira_id + '/issue', data_dict, '/rest/agile/1.0/')

        # Field 'creator' cannot be set. It is not on the appropriate screen, or unknown.
        # if 'creator_id' in vals:
        #     jira_dict['fields']['creator'] = dict(name=self.env['res.users'].browse(vals['creator_id']).jira_id)

        if 'stage_id' in vals and type == 'WRITE':
            stage_obj = self.env['project.task.type'].browse(vals['stage_id'])
            if not stage_obj.jira_id:
                raise exceptions.ValidationError('Selected stage must be connected to jira')
            response = self.env.ref('jira_connector.jira_settings_record').get('issue/' + self.key + '/transitions').json()
            allowed_transitions = dict()
            for t in response['transitions']:
                allowed_transitions[int(t['to']['id'])] = int(t['id'])
            if int(stage_obj.jira_id) not in allowed_transitions:
                raise exceptions.ValidationError('Unallowed transition')
            response = self.env.ref('jira_connector.jira_settings_record').post('issue/' + self.key + '/transitions',
                                    dict(transition=dict(id=allowed_transitions[int(stage_obj.jira_id)])))

        if 'resolution_id' in vals and type == 'WRITE':
            jira_dict['fields']['resolution'] = dict(name=self.env['jira.issue.resolution'].browse(vals['resolution_id']).name)

        if 'parent_id' in vals:
            if vals['parent_id']:
                jira_dict['fields']['parent'] = dict(key=self.env['project.task'].browse(vals['parent_id']).key)
            # not supported
            # else:
            #     jira_dict['fields']['parent'] = {}

        return jira_dict

    @api.model
    def create(self, vals):
        issue = super(JiraIssue, self).create(vals)
        if 'disable_mail_mail' not in self.env.context and issue.project_id.jira_project:
            issue_dict = issue.create_jira_dict(vals, 'CREATE')
            response = self.env.ref('jira_connector.jira_settings_record').post('issue', issue_dict)
            issue.write(dict(
                jira_id=response.json()['id'],
                key=response.json()['key']
            ))

            for s in issue.sprint_ids:
                data_dict = dict(issues=[issue.key])
                self.env.ref('jira_connector.jira_settings_record').post('sprint/' + s.jira_id + '/issue', data_dict, '/rest/agile/1.0/')

            if issue.stage_id:
                # update jira stage
                issue.write(dict(stage_id=issue.stage_id.id))

            self = self.with_context(dict(disable_mail_mail=True))
            self.jira_parse_response(
                self.env.ref('jira_connector.jira_settings_record').get('issue/' + issue.jira_id).json())

            if issue.resolution_id:
                self.env.ref('jira_connector.jira_settings_record').put('issue/' + self.jira_id, dict(fields=dict(resolution=dict(id=issue.resolution_id.jira_id))))

        return issue

    @api.one
    def write(self, vals):
        issue = super(JiraIssue, self).write(vals)
        if 'disable_mail_mail' not in self.env.context and self.jira_id:
            issue_dict = self.create_jira_dict(vals, 'WRITE')
            if issue_dict['fields']:
                response = self.env.ref('jira_connector.jira_settings_record').put('issue/' + self.jira_id, issue_dict)
        return issue

    @api.one
    def unlink(self):

        jira_id = self.jira_id

        output = super(JiraIssue, self).unlink()

        if jira_id:
            self.env.ref('jira_connector.jira_settings_record').delete('issue/' + jira_id)

        return output

    def jira_get_all(self):
        response = self.env.ref('jira_connector.jira_settings_record').getall(
            'search?includeInactive=True&fields=*all&validateQuery=strict&jql=ORDER BY updatedDate asc')
        for r in response:
            self.jira_parse_response(r, True)
            self.env.cr.commit()

    def jira_get_last_day(self):
        response = self.env.ref('jira_connector.jira_settings_record').getall(
            'search?includeInactive=True&fields=*all&validateQuery=strict&jql=updatedDate >= "-1d" ORDER BY updatedDate asc')
        for r in response:
            self.jira_parse_response(r, True)
            self.env.cr.commit()

    @api.one
    def update_jira(self):
        ctx = dict(self.env.context)
        ctx['disable_mail_mail'] = True
        ctx['disable_mail_message'] = True
        ctx['mail_create_nosubscribe'] = True
        self = self.with_context(ctx)
        self.jira_parse_response(self.env.ref('jira_connector.jira_settings_record').get(
            'search?includeInactive=True&fields=*all&validateQuery=strict&jql=key=' + self.key).json()['issues'][0])

    def jira_parse_response(self, response, update=False):
        issue = self.search([('key', '=', response['key'])])
        if issue:
            if issue.jira_update == fields.Datetime.to_string(parser.parse(response['fields']['updated'])):
                print('SKIP')
                return issue
        issue_dict = dict(
            jira_id=response['id'],
            key=response['key'],
            name=response['fields']['summary'],
            issue_type_id=self.env['jira.issue.type'].jira_dict(response['fields']['issuetype']).id,
            project_id=self.env['project.project'].jira_key(response['fields']['project']['key']).id,
            resolution_id=False,
            resolution_date=False,
            jira_create=parser.parse(response['fields']['created']),
            jira_update=parser.parse(response['fields']['updated']),
            priority_id=False,
            user_id=False,
            stage_id=self.env['project.task.type'].jira_dict(response['fields']['status']).id,
            description=False,
            creator_id=self.env['res.users'].get_user_by_dict(response['fields']['creator']).id,
            reporter_id=self.env['res.users'].get_user_by_dict(response['fields']['reporter']).id,
            parent_id=False,
            epic_id=False,
            sprint_ids=[(6, 0, [])],
            date_deadline=False,
            planned_hours=False,
            tag_ids=[(6, 0, [])],
            version_ids=[(6, 0, [])],
            fix_version_ids=[(6, 0, [])],
            component_ids=[(6, 0, [])],
        )
        if response['fields']['description']:
            issue_dict['description'] = markdown(response['fields']['description'])
        if response['fields']['resolution']:
            issue_dict['resolution_id'] = self.env['jira.issue.resolution'].jira_key(response['fields']['resolution']['id']).id
        if response['fields']['resolutiondate']:
            issue_dict['resolution_date'] = parser.parse(response['fields']['resolutiondate'])
        if 'assignee' in response['fields'] and response['fields']['assignee']:
            issue_dict['user_id'] = self.env['res.users'].get_user_by_dict(response['fields']['assignee']).id
        if 'priority' in response['fields'] and response['fields']['priority']:
            issue_dict['priority_id'] = self.env['jira.issue.priority'].jira_key(response['fields']['priority']['id']).id
        if 'parent' in response['fields'] and response['fields']['parent']:
            issue_dict['parent_id'] = self.jira_key(response['fields']['parent']['key']).id
        if self.env['jira.field'].jira_key('Epic Link'):
            if response['fields'][self.env['jira.field'].jira_key('Epic Link').jira_id]:
                issue_dict['epic_id'] = self.jira_key(response['fields'][self.env['jira.field'].jira_key('Epic Link').jira_id]).id
        if 'duedate' in response['fields'] and response['fields']['duedate']:
            issue_dict['date_deadline'] = parser.parse(response['fields']['duedate'])
        if 'timeestimate' in response['fields'] and response['fields']['timeestimate']:
            issue_dict['planned_hours'] = response['fields']['timeestimate']/3600.0
        if self.env['jira.field'].jira_key('Sprint'):
            if response['fields'][self.env['jira.field'].jira_key('Sprint').jira_id]:
                sprints = response['fields'][self.env['jira.field'].jira_key('Sprint').jira_id]
                sprint_ids = []
                for s in sprints:
                    sprint_id = re.search('\\[id=(\\d*),rapidViewId', s).group(1)
                    sprint = self.env['jira.sprint'].jira_key(sprint_id)
                    if issue_dict['project_id'] not in sprint.project_ids.ids:
                        sprint.project_ids = [issue_dict['project_id']]
                    sprint_ids.append(sprint.id)
                    issue_dict['sprint_ids'] = [(6, 0, sprint_ids)]
        if response['fields']['labels']:
            tags = list()
            for l in response['fields']['labels']:
                tag = self.env['project.tags'].search([('name', '=', l)])
                if not tag:
                    tag = tag.create(dict(name=l))
                tags.append(tag.id)
            issue_dict['tag_ids'] = [(6, 0, tags)]
        if 'versions' in response['fields'] and response['fields']['versions']:
            version_list = list()
            for version in response['fields']['versions']:
                version['projectId'] = response['fields']['project']['id']
                version_list.append(self.env['jira.project.version'].jira_dict(version).id)
            issue_dict['version_ids'] = [(6, 0, version_list)]
        if 'fixVersions' in response['fields'] and response['fields']['fixVersions']:
            version_list = list()
            for version in response['fields']['fixVersions']:
                version['projectId'] = response['fields']['project']['id']
                version_list.append(self.env['jira.project.version'].jira_dict(version).id)
            issue_dict['fix_version_ids'] = [(6, 0, version_list)]

        if 'components' in response['fields'] and response['fields']['components']:
            component_ids = list()
            for c in response['fields']['components']:
                component_ids.append(self.env['jira.project.component'].jira_key(c['id']).id)
            issue_dict['component_ids'] = [(6, 0, component_ids)]

        issue = self.search([('key', '=', issue_dict['key'])])
        if not issue:
            issue = self.create(issue_dict)
            print('#####', 'CREATE', parser.parse(response['fields']['updated']), issue.key)
        else:
            issue.write(issue_dict)
            print('#####', 'UPDATE', parser.parse(response['fields']['updated']), issue.key)
        if update:
            self.env.ref('jira_connector.jira_settings_record').updated = parser.parse(response['fields']['updated']).date()

        if response['fields']['comment']['total'] > response['fields']['comment']['maxResults']:
            int('a')
            self.env['mail.message'].jira_get_all(issue)
        else:
            for comment in response['fields']['comment']['comments']:
                self.with_context(dict(
                    disable_mail_mail=True
                )).env['mail.message'].jira_parse_response(issue, comment)

        if 'worklog' in response['fields']:
            if response['fields']['worklog']['total'] > response['fields']['worklog']['maxResults']:
                self.env['account.analytic.line'].jira_get_all(issue)
            else:
                for w in response['fields']['worklog']['worklogs']:
                    self.env['account.analytic.line'].jira_parse_response(issue, w)

        if self.env.ref('jira_connector.jira_settings_record').download_attachments:
            for a in response['fields']['attachment']:
                self.env['ir.attachment'].create_attachemnt_from_response(issue, a)

        for l in response['fields']['issuelinks']:
            self.env['jira.issue.link'].jira_parse_response(issue, l)

        return issue

    def jira_key(self, key):
        issue = self.search([('key', '=', key)])
        if not issue:
            issue = self.jira_parse_response(
                self.env.ref('jira_connector.jira_settings_record').get(
                    'search?includeInactive=True&fields=*all&validateQuery=strict&jql=key=' + key).json()['issues'][0]
            )
        return issue

    @api.onchange('jira_project')
    def onchange_context(self):
        if self.jira_project:
            if self.user_id and not self.user_id.jira_id:
                self.user_id = False
            if self.reporter_id and not self.reporter_id.jira_id:
                self.reporter_id = False
            if self.creator_id and not self.creator_id.jira_id:
                self.creator_id = False
            return {'domain': {'user_id': [('jira_id', '!=', False)],
                               'reporter_id': [('jira_id', '!=', False)],
                               'creator_id': [('jira_id', '!=', False)]}}
        else:
            return {'domain': {'user_id': [],
                               'reporter_id': [],
                               'creator_id': []}}

    @api.multi
    @api.depends('key')
    def name_get(self):
        result = []
        for issue in self:
            if issue.key:
                result.append((issue.id, '[' + issue.key + '] ' + issue.name))
            else:
                result.append((issue.id, issue.name))
        return result

    @api.one
    @api.depends('issue_type_id', 'issue_type_id.name')
    def compute_is_epic(self):
        if self.issue_type_id and self.issue_type_id.name == 'Epic':
            self.is_epic = True
        elif self.issue_type_id and self.issue_type_id.name == 'Sub-task':
            self.is_subtask = True

    @api.one
    def compute_epic_issues_count(self):
        self.epic_issues_count = len(self.epic_ids)

    jira_id = fields.Char()
    key = fields.Char()

    # summary
    # name = fields.Char()
    # description = fields.Html()

    # time_original_estimate = fields.Float()
    # time_estimate = fields.Float()
    resolution_date = fields.Datetime()
    jira_create = fields.Datetime(string='Created [JIRA]')
    jira_update = fields.Datetime(string='Updated [JIRA]')
    # due_date = fields.Date() - date_deadline

    creator_id = fields.Many2one('res.users', string='Creator')
    reporter_id = fields.Many2one('res.users', string='Reporter')
    # assignee_id = fields.Many2one('res.users') - user_id
    user_id = fields.Many2one(default=False)

    epic_id = fields.Many2one('project.task', string='Epic')
    epic_ids = fields.One2many('project.task', 'epic_id', string='Issues in epic')
    epic_issues_count = fields.Integer(compute=compute_epic_issues_count)

    issue_type_id = fields.Many2one('jira.issue.type')
    component_ids = fields.Many2many('jira.project.component')
    # project_id = fields.Many2one('project.project')
    version_ids = fields.Many2many('jira.project.version', relation='issueversion1')
    fix_version_ids = fields.Many2many('jira.project.version', relation='issueversion2')
    resolution_id = fields.Many2one('jira.issue.resolution')
    # parent_id = fields.Many2one('project.task') - parent_id
    # subtask_ids = fields.One2many('project.task', 'parent_id') - child_ids
    priority_id = fields.Many2one('jira.issue.priority')
    # comment_ids = fields.One2many('mail.message', 'issue_id')
    # worklog_ids = fields.One2many('jira.issue.worklog', 'issue_id')
    # status_id = fields.Many2one('project.task.type') -- stage_id
    sprint_ids = fields.Many2many('jira.sprint', string='Sprints')
    is_epic = fields.Boolean(compute=compute_is_epic, store=True)
    is_subtask = fields.Boolean(compute=compute_is_epic, store=True)

    link_ids = fields.One2many('jira.issue.link.single', 'task_id')

    jira_project = fields.Boolean(related='project_id.jira_project')
    issue_type_ids = fields.Many2many(related='project_id.issue_type_ids')
