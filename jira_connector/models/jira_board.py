# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions


class JiraBoard(models.Model):

    _name = 'jira.board'
    _description = 'Jira Board'

    def create_jira_dict(self, vals, type):
        jira_dict = dict()
        if 'name' in vals:
            jira_dict['name'] = vals['name']
        if 'type' in vals:
            jira_dict['type'] = vals['type']
        if 'project_id' in vals:
            jira_dict['location'] = dict(
                projectKeyOrId=self.env['project.project'].browse(vals['project_id']).key,
                type='string'
            )
        if 'filter_id' in vals:
            jira_dict['filterId'] = self.env['jira.filter'].browse(vals['filter_id']).jira_id

        return jira_dict

    @api.model
    def create(self, vals):
        board = super(JiraBoard, self).create(vals)
        if 'disable_mail_mail' not in self.env.context:
            board_dict = board.create_jira_dict(vals, 'CREATE')
            response = self.env.ref('jira_connector.jira_settings_record').post('sprint', board_dict, '/rest/agile/1.0/').json()
            board.jira_id = response['id']
        return board

    def jira_get_all(self):
        boards = self.env.ref('jira_connector.jira_settings_record').getall('board?maxResults=50', '/rest/agile/latest/', 'values')
        for b in boards:
            self.jira_parse_response(b)

    def jira_parse_response(self, response):
        board_dict = dict(
            jira_id=response['id'],
            name=response['name'],
            type=response['type'],
        )

        projects = self.env.ref('jira_connector.jira_settings_record').getall(
            'board/' + str(board_dict['jira_id']) + '/project?maxResults=50', '/rest/agile/latest/', 'values')
        project_ids = []
        for p in projects:
            project_ids.append(self.env['project.project'].jira_key(p['key']).id)
        board_dict['project_ids'] = [(6, 0, project_ids)]

        try:
            sprints = self.env.ref('jira_connector.jira_settings_record').getall(
                'board/' + str(board_dict['jira_id']) + '/sprint?maxResults=50', '/rest/agile/latest/', 'values')
            sprint_ids = []
            for s in sprints:
                sprint_ids.append(self.env['jira.sprint'].jira_key(str(s['id'])).id)
                self.env['jira.sprint'].jira_parse_response(s)
            board_dict['sprint_ids'] = [(6, 0, sprint_ids)]
        except:
            pass

        board = self.search([('jira_id', '=', response['id'])])

        if not board:
            board = self.create(board_dict)
        else:
            board.write(board_dict)

        return board

    def jira_key(self, id):
        board = self.search([('jira_id', '=', 'id')])
        if not board:
            board = self.jira_parse_response(
                self.env.ref('jira_connector.jira_settings_record').get('board/' + id, '/rest/agile/latest/').json()
            )
        return board

    jira_id = fields.Char()
    name = fields.Char(required=1)
    type = fields.Selection([('scrum', 'scrum'),
                             ('kanban', 'kanban')], required=1)
    project_ids = fields.Many2many('project.project')
    project_id = fields.Many2one('project.project')
    filter_id = fields.Many2one('jira.filter')
    sprint_ids = fields.Many2many('jira.sprint')
    location = fields.Selection([('project', 'project'),
                                 ('user', 'user')])
