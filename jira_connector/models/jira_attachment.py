# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions
from dateutil import parser
import base64
from odoo.tools.config import configmanager


class JiraIssueAttachment(models.Model):

    _inherit = 'ir.attachment'

    def send_to_jira(self):
        if self.res_model == 'project.task':
            task = self.env['project.task'].browse(self.res_id)
            if task.jira_id:
                filepath = self.env['ir.attachment']._filestore() + '/' + self.store_fname
                response = self.env.ref('jira_connector.jira_settings_record').post_file('issue/' + task.jira_id + '/attachments',
                            filename=self.datas_fname, filepath=filepath)
                self.jira_id = response.json()[0]['id']

    @api.model
    def create(self, vals):
        attachment = super(JiraIssueAttachment, self).create(vals)
        if 'disable_mail_mail' not in self.env.context:
            attachment.send_to_jira()
        return attachment

    def create_attachemnt_from_response(self, issue, response):
        if not self.search([('jira_id', '=', response['id'])]):
            resp = self.env.ref('jira_connector.jira_settings_record').get_file(response['content']).content
            self.create(dict(
                datas=base64.b64encode(resp),
                name=response['filename'],
                datas_fname=response['filename'],
                res_model='project.task',
                res_id=issue.id,
                jira_id=response['id'],
                issue_id=issue.id,
                author_id=self.env['res.users'].get_user_by_dict(response['author']).id,
                jira_created=parser.parse(response['created']),
            ))

    jira_id = fields.Char(string='Jira ID')
    issue_id = fields.Many2one('project.task')
    author_id = fields.Many2one('res.users')
    jira_created = fields.Datetime()
