# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions
import sys


class JiraUser(models.Model):

    _inherit = 'res.users'

    def action_reset_password(self):
        if 'disable_mail_mail' in self.env.context:
            return
        super(JiraUser, self).action_reset_password()

    def jira_get_all(self):
        response = self.env.ref('jira_connector.jira_settings_record').getall('user/search?username="."&includeInactive=true')
        for r in response:
            self.jira_parse_response(r)

    def jira_parse_response(self, response):
        if 'errorMessages' in response:
            key = response['errorMessages'][0][len('The user with the key \''):-len('\' does not exist')]
            user_dict = dict(
                jira_id=key,
                short_name=key,
                login=key,
                name=key,
                jira_active=False,
            )
        else:
            if 'emailAddress' not in response:
                login = response['name']
                email = response['name']
            else:
                login = response['emailAddress']
                email = response['emailAddress']

            user_dict = dict(
                jira_id=response['key'],
                short_name=response['name'],
                login=login,
                email=email,
                name=response['displayName'],
                jira_active=response['active'],
            )
        user = self.env['res.users'].search([('login', '=', user_dict['login'])])
        if not user:
            user = self.env['res.users'].create(user_dict)
            self.env['hr.employee'].create(dict(user_id=user.id))
        else:
            user.write(user_dict)
        return user

    def jira_key(self, key):
        user = self.search([('jira_id', '=', key)])
        if not user:
            user = self.jira_parse_response(self.env.ref('jira_connector.jira_settings_record').get('user?key=' + key, check=False).json())
        return user

    def jira_short_name(self, name):
        # stupid jira filter api
        user = self.search([('short_name', '=', name)])
        if not user:
            self.jira_get_all()
            user = self.search([('short_name', '=', name)])
        return user

    def get_user_by_dict(self, user_dict):
        if 'key' in user_dict:
            return self.jira_key(user_dict['key'])
        else:
            return self.jira_key(user_dict['name'])

    jira_id = fields.Char()
    short_name = fields.Char()
    #email = fields.Char(required=1) - login
    name = fields.Char(required=1)
    jira_active = fields.Boolean(default=False)
