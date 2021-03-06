# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions


class JiraIssueStatus(models.Model):

    _inherit = 'project.task.type'

    def jira_get_all(self):
        status = self.env.ref('jira_connector.jira_settings_record').get('status').json()
        for s in status:
            self.jira_parse_response(s)

    def jira_parse_response(self, response):
        status_dict = dict(
            jira_id=response['id'],
            name=response['name'],
            description=response['description'],
            category_id=self.env['jira.issue.status.category'].jira_key(response['statusCategory']['key']).id,
        )
        status = self.search([('jira_id', '=', status_dict['jira_id'])])
        if not status:
            status = self.create(status_dict)
        else:
            status.write(status_dict)
        return status

    def jira_key(self, id):
        status = self.search([('jira_id', '=', id)])
        if not status:
            status = self.jira_parse_response(
                self.env.ref('jira_connector.jira_settings_record').get('status/' + id).json()
            )
        return status

    def jira_dict(self, status_dict):
        status = self.search([('jira_id', '=', status_dict['id'])])
        if not status:
            status = self.jira_parse_response(status_dict)
        return status

    jira_id = fields.Char()
    # name = fields.Char(required=1)
    # description = fields.Char(required=1)
    category_id = fields.Many2one('jira.issue.status.category')
