from django import template
from django.utils.safestring import mark_safe

register = template.Library()


class RecurseReportSummaryTree(template.Node):
    def __init__(self, template_nodes, config_var):
        self.template_nodes = template_nodes
        self.config_var = config_var

    def _render_node(self, context, node):
        context.push()
        context['node'] = node
        if "children" in node:
            children = [self._render_node(context, x) for x in node["children"]]
            context['children'] = mark_safe(''.join(children))
        rendered = self.template_nodes.render(context)
        context.pop()
        return rendered

    def render(self, context):
        return self._render_node(context, self.config_var.resolve(context))


@register.tag
def recurseroot(parser, token):
    bits = token.contents.split()
    if len(bits) != 2:
        raise template.TemplateSyntaxError(_('%s tag requires a root') % bits[0])  # noqa

    config_var = template.Variable(bits[1])

    template_nodes = parser.parse(('endrecurseroot',))
    parser.delete_first_token()

    return RecurseReportSummaryTree(template_nodes, config_var)
