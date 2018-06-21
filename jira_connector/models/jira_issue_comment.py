# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions
from dateutil import parser
try:
    from markdown import markdown
except:
    pass


class MailThread(models.AbstractModel):

    _inherit = 'mail.thread'

    @api.multi
    def message_auto_subscribe(self, updated_fields, values=None):
        new_partners, new_channels = dict(), dict()
        user_field_lst = self._message_get_auto_subscribe_fields(updated_fields)
        subtypes, relation_fields = self.env['mail.message.subtype'].auto_subscribe_subtypes(self._name)
        if not any(relation in relation_fields for relation in updated_fields) and not user_field_lst:
            return True
        headers = set()
        for subtype in subtypes:
            if subtype.relation_field and values.get(subtype.relation_field):
                headers.add((subtype.res_model, values.get(subtype.relation_field)))
        if headers:
            header_domain = ['|'] * (len(headers) - 1)
            for header in headers:
                header_domain += ['&', ('res_model', '=', header[0]), ('res_id', '=', header[1])]
            for header_follower in self.env['mail.followers'].sudo().search(header_domain):
                for subtype in header_follower.subtype_ids:
                    if subtype.parent_id and subtype.parent_id.res_model == self._name:
                        new_subtype = subtype.parent_id
                    elif subtype.res_model is False:
                        new_subtype = subtype
                    else:
                        continue
                    if header_follower.partner_id:
                        new_partners.setdefault(header_follower.partner_id.id, set()).add(new_subtype.id)
                    else:
                        new_channels.setdefault(header_follower.channel_id.id, set()).add(new_subtype.id)
        to_add_users = self.env['res.users'].sudo().browse(
            [values[name] for name in user_field_lst if values.get(name)])
        for partner in to_add_users.mapped('partner_id'):
            new_partners.setdefault(partner.id, None)
        for pid, subtypes in new_partners.items():
            subtypes = list(subtypes) if subtypes is not None else None
            self.message_subscribe(partner_ids=[pid], subtype_ids=subtypes, force=(subtypes != None))
        for cid, subtypes in new_channels.items():
            subtypes = list(subtypes) if subtypes is not None else None
            self.message_subscribe(channel_ids=[cid], subtype_ids=subtypes, force=(subtypes != None))
        user_pids = [user.partner_id.id for user in to_add_users if
                     user != self.env.user and user.notification_type == 'email']
        if 'disable_mail_mail' not in self.env.context:
            self._message_auto_subscribe_notify(user_pids)
        return True


class MailMail(models.Model):

    _inherit = 'mail.mail'

    @api.model
    def create(self, vals):
        if 'disable_mail_mail' in self.env.context:
            return
        return super(MailMail, self).create(vals)


class ResPartner(models.Model):

    _inherit = 'res.partner'

    @api.multi
    def _notify(self, message, force_send=False, send_after_commit=True, user_signature=True):
        if 'disable_mail_mail' in self.env.context:
            return True
        super(ResPartner, self)._notify(message, force_send, send_after_commit, user_signature)


class JiraIssueComment(models.Model):

    _inherit = 'mail.message'

    @api.model
    def create(self, vals):
        if 'disable_mail_message' in self.env.context:
            return
        return super(JiraIssueComment, self).create(vals)

    # @api.multi
    # def _notify(self, force_send=False, send_after_commit=True, user_signature=True):
    #     if 'disable_mail_mail' in self.env.context:
    #         return
    #     return super(JiraIssueComment, self)._notify(self, force_send, send_after_commit, user_signature)

    def jira_get_all(self, issue):
        int('a')

    def jira_parse_response(self, issue, response):
        comment_dict = dict(
            jira_id=response['id'],
            author_id=self.env['res.users'].get_user_by_dict(response['author']).partner_id.id,
            update_author_id=self.env['res.users'].get_user_by_dict(response['updateAuthor']).partner_id.id,
            body=markdown(response['body']),
            date=parser.parse(response['created']),
            updated=parser.parse(response['updated']),
            model='project.task',
            res_id=issue.id,
            message_type='comment',
            subtype_id=1,
        )
        comment = self.search([('jira_id', '=', comment_dict['jira_id'])])
        if not comment:
            comment = self.create(comment_dict)
        else:
            comment.write(comment_dict)
        return comment

    def jira_key(self, issue, id):
        pass

    jira_id = fields.Char()
    # issue_id = fields.Many2one('project.task', required=1)
    # author_id = fields.Many2one('res.users', required=1) - author_id
    update_author_id = fields.Many2one('res.partner')
    # body = fields.Html(required=1) -- body
    # created = fields.Datetime(required=1) -- date
    updated = fields.Datetime()
