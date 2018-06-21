# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions


class JiraFilter(models.Model):

    _name = 'jira.filter'
    _description = 'Jira Filter'

    def jira_get_all(self):
        # /rest/greenhopper/1.0/savedfilter/list
        filters = self.env.ref('jira_connector.jira_settings_record').get('savedfilter/list', '/rest/greenhopper/1.0/').json()
        for f in filters['filters']:
            self.jira_parse_response(f)

    def jira_parse_response(self, response):
        filter_dict = dict(
            jira_id=response['id'],
            name=response['name'],
            query=response['query'],
            owner_id=self.env['res.users'].jira_short_name(response['owner']['userName']).id,
            description=False
        )
        if 'description' in response:
            filter_dict['description'] = response['description']
        filter = self.search([('jira_id', '=', filter_dict['jira_id'])])
        if not filter:
            filter = self.create(filter_dict)
        else:
            filter.write(filter_dict)
        return filter

    jira_id = fields.Char()
    name = fields.Char()
    description = fields.Char()
    owner_id = fields.Many2one('res.users')
    query = fields.Char()
