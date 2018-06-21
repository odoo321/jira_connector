# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions



class JiraProject(models.Model):

    _inherit = 'project.project'

    def create_jira_dict(self, vals):
        project_dict = dict()
        if 'name' in vals:
            project_dict['name'] = vals['name']
        if 'key' in vals:
            project_dict['key'] = vals['key']
        if 'project_type_id' in vals:
            project_dict['projectTypeKey'] = self.env['jira.project.type'].browse(vals['project_type_id']).key
        if 'user_id' in vals:
            project_dict['lead'] = self.env['res.users'].browse(vals['user_id']).jira_id
        if 'project_template_id' in vals:
            project_dict['projectTemplateKey'] = self.env['jira.project.template'].browse(vals['project_template_id']).key
        if 'description' in vals:
            if vals['description']:
                project_dict['description'] = vals['description']
            else:
                project_dict['description'] = ''
        if 'url' in vals:
            if vals['url']:
                project_dict['url'] = vals['url']
            else:
                project_dict['url'] = ''
        if 'category_id' in vals:
            if vals['category_id']:
                project_dict['categoryId'] = self.env['jira.project.category'].browse(vals['category_id']).jira_id
            else:
                # raise exceptions.Warning('Setting project category to None via rest api do not work [Jira bug]')
                project_dict['categoryId'] = ''

        # if 'issue_type_ids' in vals:
        #     issue_type_list = list()
        #     for t in self.issue_type_ids:
        #         issue_type_list.append(dict(id=t.jira_id))
        #     project_dict = dict(
        #         issueTypes=issue_type_list,
        #     )
        #     response = self.env.ref('jira_connector.jira_settings_record').put('project/' + self.jira_id, project_dict)
        #     self.env.ref('jira_connector.jira_settings_record').check_response(response)

        return project_dict

    @api.model
    def create(self, vals):

        response = False
        if 'disable_mail_mail' not in self.env.context and 'jira_project' in vals and vals['jira_project']:
            project_dict = self.create_jira_dict(vals)
            response = self.env.ref('jira_connector.jira_settings_record').post('project', project_dict)
            vals['jira_id'] = response.json()['id']

        project = super(JiraProject, self).create(vals)
        if response:

            # if 'component_ids' in vals and vals['component_ids']:
            #     for c in project.component_ids:
            #         c.send_to_jira()
            # if 'version_ids' in vals and vals['version_ids']:
            #     for v in project.version_ids:
            #         v.send_to_jira()

            self = self.with_context(dict(disable_mail_mail=True))
            self.jira_parse_response(self.env.ref('jira_connector.jira_settings_record').get('project/' + project.jira_id).json())
        return project

    @api.one
    def write(self, vals):
        output = super(JiraProject, self).write(vals)
        if 'disable_mail_mail' not in self.env.context and self.jira_id:
            project_dict = self.create_jira_dict(vals)
            if project_dict:
                response = self.env.ref('jira_connector.jira_settings_record').put('project/' + self.jira_id, project_dict)
                if 'project_type_id' in vals:
                    response = self.env.ref('jira_connector.jira_settings_record').put('project/' + self.jira_id + '/type/' + self.project_type_id.key)
            # if 'component_ids' in vals and vals['component_ids']:
            #     for c in self.component_ids:
            #         c.send_to_jira()
            # if 'verison_ids' in vals and vals['version_ids']:
            #     for v in self.version_ids:
            #         v.send_to_jira()
        return output

    @api.one
    def unlink(self):
        jira_id = self.jira_id
        output = super(JiraProject, self).unlink()
        if jira_id:
            response = self.env.ref('jira_connector.jira_settings_record').delete('project/' + jira_id)
        return output

    @api.onchange('jira_project')
    def onchange_context(self):
        if self.jira_project:
            if self.user_id and not self.user_id.jira_id:
                self.user_id = False
            return {'domain': {'user_id': [('jira_id', '!=', False)]}}
        else:
            return {'domain': {'user_id': []}}

    def jira_get_all(self):
        response = self.env.ref('jira_connector.jira_settings_record').get('project').json()
        for p in response:
            self.jira_parse_response(self.env.ref('jira_connector.jira_settings_record').get('project/' + p['key']).json())

    def jira_parse_response(self, response):
        project_dict = dict(
            jira_id=response['id'],
            key=response['key'],
            description=False,
            user_id=self.env['res.users'].get_user_by_dict(response['lead']).id,
            name=response['name'],
            project_type_id=self.env['jira.project.type'].jira_key(response['projectTypeKey']).id,
            category_id=False,
            url=False,
            type_ids=[(6, 0, [])],
        )

        if 'projectCategory' in response:
            project_dict['category_id'] = self.env['jira.project.category'].jira_key(response['projectCategory']['id']).id
        if 'url' in response:
            project_dict['url'] = response['url']
        if response['description']:
            project_dict['description'] = response['description']

        issue_type_ids = list()
        for issue_type in response['issueTypes']:
            issue_type_ids.append(self.env['jira.issue.type'].jira_dict(issue_type).id)
        project_dict['issue_type_ids'] = [(6, 0, issue_type_ids)]

        types = self.env.ref('jira_connector.jira_settings_record').get('project/' + response['key'] + '/statuses').json()[0]['statuses']
        type_ids = []
        for t in types:
            type_ids.append(self.env['project.task.type'].jira_dict(t).id)
        project_dict['type_ids'] = [(6, 0, type_ids)]

        project = self.search([('key', '=', project_dict['key'])])
        if not project:
            project = self.create(project_dict)
        else:
            project.write(project_dict)

        for component in response['components']:
            self.env['jira.project.component'].jira_key(component['id'])

        for version in response['versions']:
            self.env['jira.project.version'].jira_dict(version)

        return project

    def jira_key(self, key):
        project = self.search([('key', '=', key)])
        if not project:
            project = self.jira_parse_response(
                self.env.ref('jira_connector.jira_settings_record').get('project/' + key).json()
            )
        return project

    def get_jira_id(self, id):
        project = self.search([('jira_id', '=', id)])
        if not project:
            project = self.jira_parse_response(
                self.env.ref('jira_connector.jira_settings_record').get('project/' + id).json()
            )

        return project

    @api.multi
    @api.depends('key')
    def name_get(self):
        result = []
        for project in self:
            if project.key:
                result.append((project.id, '[' + project.key + '] ' + project.name))
            else:
                result.append((project.id, project.name))
        return result

    jira_id = fields.Char()
    key = fields.Char()

    # name = fields.Char()commit
    description = fields.Html()
    url = fields.Char()

    #lead_id = fields.Many2one('res.users') -- user_id
    user_id = fields.Many2one(default=False)
    project_type_id = fields.Many2one('jira.project.type')
    project_template_id = fields.Many2one('jira.project.template')
    category_id = fields.Many2one('jira.project.category')

    component_ids = fields.One2many('jira.project.component', 'project_id', string='Components')
    issue_type_ids = fields.Many2many('jira.issue.type', string='Issue Types')
    version_ids = fields.One2many('jira.project.version', 'project_id', string='Versions')
    jira_project = fields.Boolean(default=True)

    @api.one
    def _compute_sprint_count(self):
        self.sprint_count = len(self.env['jira.sprint'].search([('project_ids', '=', self.id)]))

    sprint_count = fields.Integer(compute='_compute_sprint_count', string='Sprints')
