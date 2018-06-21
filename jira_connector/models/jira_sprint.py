# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions
from dateutil import parser


class JiraSprint(models.Model):

    _name = 'jira.sprint'
    _description = 'Jira Sprint'

    def create_jira_dict(self, vals, type):
        jira_dict = dict()
        if 'name' in vals:
            jira_dict['name'] = vals['name']
        if 'board_id' in vals:
            jira_dict['originBoardId'] = self.env['jira.board'].browse(vals['board_id']).jira_id
        if 'goal' in vals:
            jira_dict['goal'] = vals['goal']
        return jira_dict

    @api.model
    def create(self, vals):
        sprint = super(JiraSprint, self).create(vals)
        sprint.project_ids = [(6, 0, sprint.board_id.project_ids.ids)]
        if 'disable_mail_mail' not in self.env.context:
            sprint_dict = sprint.create_jira_dict(vals, 'CREATE')
            response = self.env.ref('jira_connector.jira_settings_record').post('sprint', sprint_dict, '/rest/agile/1.0/').json()
            sprint.jira_id = response['id']
        return sprint

    @api.one
    def write(self, vals):
        output = super(JiraSprint, self).write(vals)
        if 'disable_mail_mail' not in self.env.context:
            sprint_dict = self.create_jira_dict(vals, 'write')
            if sprint_dict:
                response = self.env.ref('jira_connector.jira_settings_record').put('sprint/' + self.jira_id, sprint_dict, '/rest/agile/1.0/').json()

    def jira_parse_response(self, response):

        sprint_dict = dict(
            jira_id=response['id'],
            state=response['state'],
            name=response['name'],
            goal=False,
            start=False,
            end=False,
            complete=False,
        )
        if 'startDate' in response and response['startDate']:
            sprint_dict['start'] = parser.parse(response['startDate'])
        if 'endDate' in response and response['endDate']:
            sprint_dict['end'] = parser.parse(response['endDate'])
        if 'completeDate' in response and response['completeDate']:
            sprint_dict['complete'] = parser.parse(response['completeDate'])
        if 'goal' in response and response['goal']:
            sprint_dict['goal'] = response['goal']

        sprint = self.search([('jira_id', '=', sprint_dict['jira_id'])])
        if not sprint:
            sprint = self.create(sprint_dict)
        else:
            sprint.write(sprint_dict)
        return sprint

    def jira_key(self, id):
        sprint = self.search([('jira_id', '=', id)])
        if not sprint:
            sprint = self.jira_parse_response(
                self.env.ref('jira_connector.jira_settings_record').get('sprint/' + id, '/rest/agile/latest/').json()
            )
        return sprint

    @api.one
    def update_boards(self):
        self.env['jira.board'].jira_get_all()

    jira_id = fields.Char()
    #selection
    state = fields.Selection([('future', 'future'),
                              ('active', 'active'),
                              ('closed', 'closed')])
    board_id = fields.Many2one('jira.board')
    name = fields.Char()
    start = fields.Datetime()
    end = fields.Datetime()
    complete = fields.Datetime()
    goal = fields.Char()
    issue_ids = fields.Many2many('project.task')
    project_ids = fields.Many2many('project.project', string='Projects')
