# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions
from dateutil import parser
import os
try:
    from markdown import markdown
except:
    pass

class JiraIssueWorklog(models.Model):

    _inherit = 'account.analytic.line'

    def create_jira_dict(self, vals, type):
        jira_dict = dict()
        if 'user_id' in vals:
            jira_dict['author'] = dict(key=self.env['res.users'].browse(vals['user_id']).jira_id)
        if 'name' in vals:
            jira_dict['comment'] = vals['name']
        if 'date' in vals:
            jira_dict['started'] = vals['date'].replace(' ', 'T') + '.000+0000'
        if 'unit_amount' in vals:
            jira_dict['timeSpentSeconds'] = int(vals['unit_amount'] * 3600.0)
        if 'task_id' in vals:
            vals['issueId'] = self.env['project.task'].browse(vals['task_id']).jira_id
        return jira_dict

    def create_tempo_dict(self, vals, type):
        jira_dict = dict()
        if 'unit_amount' in vals:
            jira_dict['timeSpentSeconds'] = int(vals['unit_amount'] * 3600.0)
            jira_dict['billedSeconds'] = int(vals['unit_amount'] * 3600.0)
        if 'name' in vals:
            jira_dict['comment'] = vals['name']
        if 'date' in vals:
            jira_dict['dateStarted'] = vals['date'].replace(' ', 'T') + '.000+0000'
        if 'user_id' in vals:
            jira_dict['author'] = dict(name=self.env['res.users'].browse(vals['user_id']).jira_id)
        if self.task_id:
            jira_dict['issue'] = dict(
                key=self.task_id.key,
                remainingEstimateSeconds=0
            )
        return jira_dict

    @api.model
    def create(self, vals):
        worklog = super(JiraIssueWorklog, self).create(vals)
        if 'disable_mail_mail' not in self.env.context and worklog.task_id.project_id.jira_project:
            if self.env.ref('jira_connector.jira_settings_record').use_tempo_timesheets is False:
                issue_dict = worklog.create_jira_dict(vals, 'CREATE')
                response = self.env.ref('jira_connector.jira_settings_record').post('issue/' + worklog.task_id.jira_id + '/worklog', issue_dict)
                worklog.write(dict(
                    jira_id=response.json()['id']
                ))
            else:
                issue_dict = worklog.create_tempo_dict(vals, 'CREATE')
                response = self.env.ref('jira_connector.jira_settings_record').post('worklogs', issue_dict, '/rest/tempo-timesheets/3/')
                worklog.write(dict(
                    jira_id=response.json()['id']
                ))

        return worklog

    @api.one
    def write(self, vals):
        output = super(JiraIssueWorklog, self).write(vals)
        if 'disable_mail_mail' not in self.env.context and self.task_id.project_id.jira_project:
            if self.env.ref('jira_connector.jira_settings_record').use_tempo_timesheets is False:
                issue_dict = self.create_jira_dict(vals, 'CREATE')
                response = self.env.ref('jira_connector.jira_settings_record').put('issue/' + self.task_id.jira_id + '/worklog/' + self.jira_id, issue_dict)
            else:
                issue_dict = self.create_tempo_dict(vals, 'CREATE')
                response = self.env.ref('jira_connector.jira_settings_record').put('worklogs/' + self.jira_id, issue_dict, '/rest/tempo-timesheets/3/')
        return output

    @api.one
    def unlink(self):
        jira_id = self.jira_id
        output = super(JiraIssueWorklog, self).unlink()
        if jira_id:
            if self.env.ref('jira_connector.jira_settings_record').use_tempo_timesheets is False:
                self.env.ref('jira_connector.jira_settings_record').delete('issue/' + self.task_id.jira_id + '/worklog/' + self.jira_id)
            else:
                self.env.ref('jira_connector.jira_settings_record').delete('worklogs/' + self.jira_id, '/rest/tempo-timesheets/3/')

    def jira_get_all(self, issue):
        for w in self.env.ref('jira_connector.jira_settings_record').get('issue/' + issue.key + '/worklog').json()['worklogs']:
            self.jira_parse_response(issue, w)

    def jira_parse_response(self, issue, response):

        user = self.env['res.users'].get_user_by_dict(response['author']).id
        employee = self.env['hr.employee'].search([('user_id', '=', user)]).id

        worklog_dict = dict(
            jira_id=response['id'],
            task_id=issue.id,
            project_id=issue.project_id.id,
            user_id=user,
            employee_id=employee,
            update_author_id=self.env['res.users'].get_user_by_dict(response['updateAuthor']).id,
            name=False,
            created=parser.parse(response['created']),
            updated=parser.parse(response['updated']),
            date=parser.parse(response['started']),
            unit_amount=response['timeSpentSeconds']/3600.0,
            account_id=issue.project_id.analytic_account_id.id,
        )
        if 'comment' in response and response['comment']:
            oldstr = markdown(response['comment'])
            newstr = ''
            for l in oldstr.split('\n'):
                if l and not l.endswith('>'):
                    newstr += l + '<br/>'
                else:
                    newstr += l
            if newstr.endswith('<br/>'):
                newstr = newstr[:-5]
            worklog_dict['name'] = newstr
        else:
            worklog_dict['name'] = markdown('Jira Worklog')
        worklog = self.search([('jira_id', '=', worklog_dict['jira_id'])])
        if not worklog:
            worklog = self.create(worklog_dict)
        else:
            worklog.write(worklog_dict)
        return worklog

    def jira_key(self, issue):
        pass

    jira_id = fields.Char()
    # issue_id = fields.Many2one('project.task') - task_id
    # author_id = fields.Many2one('res.users') - user_id
    update_author_id = fields.Many2one('res.users')
    name = fields.Html()
    created = fields.Datetime()
    updated = fields.Datetime()
    # started = fields.Datetime() - create_date
    # time = fields.Float() - unit_amount

    date = fields.Datetime(required=1, default=lambda self: fields.Datetime.now())
    unit_amount = fields.Float(required=1)
