{
    'name': 'Jira Connector',
    'version': '1.0.4',
    'summary': 'Jira Connector',
    'author': 'Grzegorz Krukar (grzegorzgk1@gmail.com)',
    'description': """
    Jira Connector
    """,
    'data': [
        'data/data.xml',
        'security/security.xml',
        'views/project.xml',
    ],
    'depends': [
        'hr_timesheet',
        'document',
    ],
    'external_dependencies': {
        'python': ['markdown']
    },
    'installable': True,
    'application': True,
    'price': 100.00,
    'currency': 'EUR',
}

# HISTORY

# VERSION - 1.0.4 [2018-04-13]
# Fix name in worklogs kanban view

# VERSION - 1.0.3 [2018-01-25]
# Some improvements

# VERSION - 1.0.2 [2018-01-18]
# Bugfix and optymalization

# VERSION - 1.0.1 [2018-01-16]
# Bugfix and basic permissions

# VERSION - 1.0.0 [2018-01-14]
# Initial release

# VERSION - 0.2.4 [2018-01-07]
# Deleting issues and issue links
# Dynamic domain
# Creation of link types
# Loggin jira requests

# VERSION - 0.2.3 [2018-01-03]
# Sending links created in odoo to jira

# VERSION - 0.2.2 [2018-01-02]
# Sending atachments to Jira
# Option to update Link Types from Jira
# Sending tempo timesheets worklogs
# Option to use tempo timesheets rest api

# VERSION - 0.2.1 [2018-01-01]
# Sending state changes and resolution
# Sending worklog information

# VERSION - 0.2.0 [2017-12-30]
# Many big changes
# Sending information to Jira

# VERSION - 0.1.2 [2017-12-18]
# Changed name to Jira Connector
# Added Cron Action
# Project and tasks are now showing/searching with corresponding key number
# Added jira fields to Project and Task views
# Working with views

# VERSION - 0.1.1 [2017-12-17]
# Conected sprint with project
# Working with views

# VERSION - 0.1.1 [2017-12-17]
# Disable sending email during jira update
# Small fixes
# Added icon

# VERSION - 0.1.0 [2017-12-17]
# Connected jira issue with odoo project task
# Connected jira user with odoo user, partner and employee
# Connected jira project with odoo project
# Connected jira issue comment with odoo mail message
# Connected jira issue status with odoo project task type
# Connected jira worklog with odoo account analytic line
# Fixed odoo bug: Project kanban unread messages [https://github.com/odoo/odoo/pull/21684]

# VERSION - 0.0.7 [2017-12-16]
# Removed some unnecessary requests.

# VERSION - 0.0.6 [2017-12-15]
# Connected Sprints with Issues

# VERSION - 0.0.5 [2017-12-15]
# Downloading boards
# Downloading sprints
# Connect board to projects and sprints

# VERSION - 0.0.4 [2017-12-14]
# Downloading jira fields
# Downloading information about issues in epic

# VERSION - 0.0.3 [2017-12-13]
# Downloading attachments
# Downloading issue links
# Only recently updated issues download data
# parent task - subtasks
# issues download in proper order (from old to new)
# Downloading worklogs

# VERSION - 0.0.2 [2017-12-12]
# Downloading issue data annd other issue related data

# VERSION - 0.0.1 [2017-12-11]
# Initial module
# Downloading project data and other project related models
