from django import template
from django.utils.safestring import mark_safe

register = template.Library()


class RecurseConfigTree(template.Node):
    def __init__(self, template_nodes, config_var):
        self.template_nodes = template_nodes
        self.config_var = config_var

    def _render_node(self, context, node):
        context.push()
        context['node'] = node
        children = [self._render_node(context, x) for x in node.children]
        if node.children:
            context['children'] = mark_safe(''.join(children))
        rendered = self.template_nodes.render(context)
        context.pop()
        return rendered

    def render(self, context):
        return self._render_node(context, self.config_var.resolve(context))


@register.tag
def recurseconfig(parser, token):
    bits = token.contents.split()
    if len(bits) != 2:
        raise template.TemplateSyntaxError(_('%s tag requires a start configuration') % bits[0])  # noqa

    config_var = template.Variable(bits[1])

    template_nodes = parser.parse(('endrecurseconfig',))
    parser.delete_first_token()

    return RecurseConfigTree(template_nodes, config_var)
