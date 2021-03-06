# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions


class JiraIssueLinkSingle(models.Model):

    _name = 'jira.issue.link.single'
    _description = 'Jira Issue Link Single'

    @api.model
    def create(self, vals):
        ilinks = list()
        if not vals['link_id']:
            link = self.env['jira.link'].browse(vals['link_name'])
            link_type = self.env['jira.issue.link.type'].search(['|', ('inward', '=', link.id), ('outward', '=', link.id)])

            if self.search([('link_name', '=', vals['link_name']), ('task_id', '=', vals['task_id'])]):
                raise exceptions.UserError('Duplicate link')

            if link.type == 'inward':
                inward_issue_id = vals['linked_task_id']
                outward_issue_id = vals['task_id']
                second_link = link_type.outward
            else:
                inward_issue_id = vals['task_id']
                outward_issue_id = vals['linked_task_id']
                second_link = link_type.inward

            issue_link = self.env['jira.issue.link'].create(dict(
                type_id=link_type.id,
                inward_issue_id=inward_issue_id,
                outward_issue_id=outward_issue_id
            ))

            vals['link_id'] = issue_link.id

            self.create(dict(
                link_name=second_link.id,
                task_id=vals['linked_task_id'],
                linked_task_id=vals['task_id'],
                link_id=issue_link.id
            ))

            issue = self.env['project.task'].browse(vals['task_id'])
            ilinks = self.env.ref('jira_connector.jira_settings_record').get('issue/' + issue.key + '?fields=issuelinks'
                                                                             ).json()['fields']['issuelinks']

        linksingle = super(JiraIssueLinkSingle, self).create(vals)

        for l in ilinks:
            self.env['jira.issue.link'].jira_parse_response(issue, l)

        return linksingle

    link_name = fields.Many2one('jira.link', required=1)
    task_id = fields.Many2one('project.task', ondelete='cascade')
    linked_task_id = fields.Many2one('project.task', ondelete='cascade')
    link_id = fields.Many2one('jira.issue.link')
    jira_id = fields.Char(related='link_id.jira_id')


class JiraIssueLink(models.Model):

    _name = 'jira.issue.link'
    _description = 'Jira Issue Link'

    def create_jira_dict(self, vals, type):
        jira_dict = dict(
            type=dict(
                name=self.type_id.name,
            ),
            inwardIssue=dict(
                key=self.inward_issue_id.key,
            ),
            outwardIssue=dict(
                key=self.outward_issue_id.key,
            )
        )
        return jira_dict

    @api.model
    def create(self, vals):
        issue_link = super(JiraIssueLink, self).create(vals)
        if 'disable_mail_mail' not in self.env.context:
            issue_dict = issue_link.create_jira_dict(vals, 'CREATE')
            response = self.env.ref('jira_connector.jira_settings_record').post('issueLink', issue_dict)
            # issue_link.write(dict(
            #     jira_id=response.json()['id'],
            # ))
        return issue_link

    @api.one
    def unlink(self):
        jira_id = self.jira_id
        output = super(JiraIssueLink, self).unlink()
        if jira_id:
            self.env.ref('jira_connector.jira_settings_record').delete('issueLink/' + jira_id)
        return output

    def jira_parse_response(self, issue, response):
        link_dict = dict(
            jira_id=response['id'],
            type_id=self.env['jira.issue.link.type'].jira_parse_response(response['type']).id,
        )
        if 'inwardIssue' in response:
            link_dict['inward_issue_id'] = self.env['project.task'].jira_key(response['inwardIssue']['key']).id
            link_dict['outward_issue_id'] = issue.id
        if 'outwardIssue' in response:
            link_dict['inward_issue_id'] = issue.id
            link_dict['outward_issue_id'] = self.env['project.task'].jira_key(response['outwardIssue']['key']).id
        #link = self.search([('jira_id', '=', link_dict['jira_id'])])
        link = self.search([
            ('type_id', '=', link_dict['type_id']),
            ('inward_issue_id', '=', link_dict['inward_issue_id']),
            ('outward_issue_id', '=', link_dict['outward_issue_id']),
        ])
        if not link:
            link = self.create(link_dict)
        else:
            link.write(link_dict)

        link.single_link_ids.unlink()
        self.env['jira.issue.link.single'].create(dict(
            link_name=link.outward.id,
            task_id=link.inward_issue_id.id,
            linked_task_id=link.outward_issue_id.id,
            link_id=link.id
        ))
        self.env['jira.issue.link.single'].create(dict(
            link_name=link.inward.id,
            task_id=link.outward_issue_id.id,
            linked_task_id=link.inward_issue_id.id,
            link_id=link.id
        ))

        return link

    jira_id = fields.Char()
    type_id = fields.Many2one('jira.issue.link.type', required=1)
    inward = fields.Many2one('jira.link', required=1, related='type_id.inward')
    outward = fields.Many2one('jira.link', required=1, related='type_id.outward')
    inward_issue_id = fields.Many2one('project.task', ondelete='cascade')
    outward_issue_id = fields.Many2one('project.task', ondelete='cascade')
    single_link_ids = fields.One2many('jira.issue.link.single', 'link_id')


class JiraIssueLinkType(models.Model):

    _name = 'jira.issue.link.type'
    _description = 'Jira Issue Link Type'

    def create_jira_dict(self, vals, type):
        jira_dict = dict()
        if 'name' in vals:
            jira_dict['name'] = vals['name']
        if 'inward' in vals:
            jira_dict['inward'] = self.env['jira.link'].browse(vals['inward']).name
        if 'outward' in vals:
            jira_dict['outward'] = self.env['jira.link'].browse(vals['outward']).name
        return jira_dict

    @api.model
    def create(self, vals):
        issue_link_type = super(JiraIssueLinkType, self).create(vals)
        if 'disable_mail_mail' not in self.env.context:
            issue_dict = issue_link_type.create_jira_dict(vals, 'CREATE')
            response = self.env.ref('jira_connector.jira_settings_record').post('issueLinkType', issue_dict)
            issue_link_type.jira_id = response.json()['id']
        return issue_link_type

    @api.one
    def write(self, vals):
        output = super(JiraIssueLinkType, self).write(vals)
        if 'disable_mail_mail' not in self.env.context:
            issue_dict = self.create_jira_dict(vals, 'WRITE')
            if issue_dict:
                self.env.ref('jira_connector.jira_settings_record').put('issueLinkType/' + self.jira_id, issue_dict)
        return output

    @api.one
    def unlink(self):
        jira_id = self.jira_id
        output = super(JiraIssueLinkType, self).unlink()
        if jira_id:
            self.env.ref('jira_connector.jira_settings_record').delete('issueLinkType/' + jira_id)
        return output

    def jira_get_all(self):
        response = self.env.ref('jira_connector.jira_settings_record').get('issueLinkType').json()
        for jilt in response['issueLinkTypes']:
            self.jira_parse_response(jilt)

    def jira_parse_response(self, response):
        link_type_dict = dict(
            jira_id=response['id'],
            name=response['name'],
            inward=self.env['jira.link'].get_object(response['inward'], 'inward').id,
            outward=self.env['jira.link'].get_object(response['outward'], 'outward').id,
        )
        link_type = self.search([('jira_id', '=', link_type_dict['jira_id'])])
        if not link_type:
            link_type = self.create(link_type_dict)
        else:
            link_type.write(link_type_dict)
        return link_type

    jira_id = fields.Char()
    name = fields.Char(required=1)

    inward = fields.Many2one('jira.link', required=1)
    outward = fields.Many2one('jira.link', required=1)


class JiraLink(models.Model):

    _name = 'jira.link'
    _description = 'Jira Link'

    def get_object(self, name, type):
        name_object = self.search([('name', '=', name), ('type', '=', type)])
        if not name_object:
            name_object = self.create(dict(name=name, type=type))
        return name_object

    @api.model
    def create(self, vals):
        link = super(JiraLink, self).create(vals)
        if link.type == 'outward' and self.search([('name', '=', link.name), ('type', '=', 'inward')]):
            link.show = False
        return link

    name = fields.Char(required=1)
    type = fields.Selection([('inward', 'inward'), ('outward', 'outward')], required=1)
    show = fields.Boolean(default=True)
