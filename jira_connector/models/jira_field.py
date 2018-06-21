# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions


class JiraField(models.Model):

    _name = 'jira.field'
    _description = 'Jira Field'

    def jira_get_all(self):
        fields = self.env.ref('jira_connector.jira_settings_record').get('field').json()
        for f in fields:
            self.jira_parse_response(f)

    def jira_parse_response(self, response):
        field_dict = dict(
            jira_id=response['id'],
            name=response['name'],
        )
        field = self.search([('name', '=', field_dict['name'])])
        if not field:
            field = self.create(field_dict)
        else:
            field.write(field_dict)
        return field

    def jira_key(self, name):
        field = self.search([('name', '=', name)])
        if not field and not self.search([]):
            self.jira_get_all()
            field = self.search([('name', '=', name)])
        return field

    jira_id = fields.Char(required=1)
    name = fields.Char(required=1)
