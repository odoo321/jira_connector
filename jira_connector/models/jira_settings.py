# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions
from datetime import datetime, date
from odoo.tools import config
import requests
import os
import logging

# path_to_data_directory = config['root_path']
# log_dir = config['root_path'] + '/jira_log/'
# if not os.path.exists(log_dir):
#     os.makedirs(log_dir)
#     os.mknod(log_dir + 'log.txt')
# logger = logging.getLogger(__name__)
# ch = logging.StreamHandler()
# fh = logging.FileHandler(log_dir + 'log.txt')
# ch.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s - %(message)s')
# ch.setFormatter(formatter)
# logger.addHandler(ch)
# logger.addHandler(fh)
# logger.propagate = False


class JiraSettings(models.Model):

    _name = 'jira.settings'
    _description = 'Jira Settings'

    # def log(self, info):
    #     logger.info(str(datetime.now()) + ' - ' + info)

    def get(self, request, path='/rest/api/latest/', check=True):
        print('GET', self.url + path + request)
        # self.log('GET ' + self.url + path + request)
        response = requests.get(self.url + path + request, auth=(self.login, self.password))
        if check:
            self.check_response(response)
        return response

    def get_file(self, url):
        print('GET', url)
        # self.log('GET ' + url)
        response = requests.get(url, auth=(self.login, self.password), stream=True)
        self.check_response(response)
        return response

    def post(self, request, rdata=dict(), path='/rest/api/latest/'):
        if self.disable_sending_data:
            return False
        print('POST', self.url + path + request, rdata)
        # self.log('POST ' + self.url + path + request + ' ' + str(rdata))

        response = requests.post(self.url + path + request, auth=(self.login, self.password), json=rdata)
        self.check_response(response)
        return response

    def post_file(self, request, filename, filepath):
        print('POST', self.url + '/rest/api/latest/' + request)
        # self.log('POST ' + self.url + '/rest/api/latest/' + request)

        attachment = open(filepath, "rb")
        response = requests.post(self.url + '/rest/api/latest/' + request, auth=(self.login, self.password),
            files={'file': (filename, attachment, 'application/octet-stream')},
            headers={'content-type': None, 'X-Atlassian-Token': 'nocheck'})
        self.check_response(response)
        return response

    def put(self, request, rdata=dict(), path='/rest/api/latest/'):
        if self.disable_sending_data:
            return False
        print('PUT', self.url + path + request, rdata)
        # self.log('PUT ' + self.url + path + request + ' ' + str(rdata))
        response = requests.put(self.url + path + request, auth=(self.login, self.password), json=rdata)
        self.check_response(response)
        return response

    def delete(self, request, path='/rest/api/latest/'):
        if self.disable_sending_data:
            return False
        print('DELETE', self.url + path + request)
        # self.log('DELETE ' + self.url + path + request)
        response = requests.delete(self.url + path + request, auth=(self.login, self.password))
        self.check_response(response)
        return response

    def check_response(self, response):
        if response is False:
            return
        if response.status_code not in [200, 201, 204, 404]:
            try:
                resp_dict = response.json()
            except:
                raise exceptions.Warning('Response status code: ' + str(response.status_code))
            error_msg = ''
            if 'errorMessages' in resp_dict and resp_dict['errorMessages']:
                for e in resp_dict['errorMessages']:
                    error_msg += e + '\n'
            if 'errors' in resp_dict and resp_dict['errors']:
                for e in resp_dict['errors']:
                    error_msg += resp_dict['errors'][e] + '\n'
            raise exceptions.Warning(error_msg)

    def getall(self, request, path='/rest/api/latest/', searchobj='issues'):
        startat = 0
        full_response = list()
        while True:
            response = self.get(request + '&startAt=' + str(startat), path).json()
            if 'errorMessages' in response:
                return full_response
            startat += 50
            if type(response) is list:
                full_response += response
                responselen = len(response)
            else:
                full_response += response[searchobj]
                responselen = len(response[searchobj])
            if responselen < 50:
                break
        return full_response

    @api.one
    def test_connection(self):
        status_code = self.get('myself').status_code
        if status_code == 200:
            raise exceptions.Warning('Settings are correct!')
        else:
            raise exceptions.Warning('Settings are not correct!')

    @api.one
    def update_jira(self):
        ctx = dict(self.env.context)
        ctx['disable_mail_mail'] = True
        ctx['disable_mail_message'] = True
        ctx['mail_create_nosubscribe'] = True
        self = self.with_context(ctx)
        models = ['jira.field', 'jira.filter', 'res.users',
                  'jira.project.category', 'jira.project.component', 'jira.project.template', 'jira.project.type', 'project.project', 
                  'jira.issue.priority', 'jira.issue.resolution', 'jira.issue.status.category', 'project.task.type', 'jira.issue.type', 'jira.issue.link.type',
                  'project.task', 'jira.board']

        if 'update' in self.env.context:
            models = [self.env.context['update']]

        for model in models:
            self.env[model].jira_get_all()

    @api.one
    def jira_get_last_day(self):
        ctx = dict(self.env.context)
        ctx['disable_mail_mail'] = True
        ctx['disable_mail_message'] = True
        ctx['mail_create_nosubscribe'] = True
        self = self.with_context(ctx)
        self.env['project.task'].jira_get_last_day()

    @api.one
    def update_jira_issues(self):
        ctx = dict(self.env.context)
        ctx['disable_mail_mail'] = True
        ctx['disable_mail_message'] = True
        ctx['mail_create_nosubscribe'] = True
        self = self.with_context(ctx)
        models = ['project.task']

        if 'update' in self.env.context:
            models = [self.env.context['update']]

        for model in models:
            self.env[model].jira_get_all()

    @api.one
    @api.constrains('url')
    def constrains_url(self):
        if not self.url:
            return
        if not self.url.startswith('http://') and not self.url.startswith('https://'):
            raise exceptions.Warning('Url must start with http:// or https://')
        if self.url.endswith('/'):
            self.url = self.url[:-1]

    name = fields.Char(default='Jira Settings')
    url = fields.Char()
    login = fields.Char()
    password = fields.Char()
    updated = fields.Date(default=date(2000, 1, 1))
    download_attachments = fields.Boolean(default=True)
    disable_sending_data = fields.Boolean(default=False)
    use_tempo_timesheets = fields.Boolean(default=False)

    cron_id = fields.Many2one('ir.cron')
    cron_active = fields.Boolean(related='cron_id.active')
    interval_number = fields.Integer(related='cron_id.interval_number')
    interval_type = fields.Selection(related='cron_id.interval_type')
    nextcall = fields.Datetime(related='cron_id.nextcall')
