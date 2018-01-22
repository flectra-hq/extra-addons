# Part of Flectra See LICENSE file for full copyright and licensing details.

from flectra import api, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.model
    def default_get(self, fields):
        result = super(ProjectProject, self).default_get(fields)
        result.update({'use_tasks': True})
        return result

    @api.model
    def create(self, vals):
        # Prevent double project creation when 'use_tasks' is checked
        self = self.with_context(project_creation_in_progress=True,
                                 mail_create_nosubscribe=True)
        return super(ProjectProject, self).create(vals)
