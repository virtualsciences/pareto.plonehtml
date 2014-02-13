from Products.ATContentTypes.content import base

from plone.portlets.interfaces import (
    IPortletManager, IPortletAssignmentMapping, IPortletRetriever,
    ILocalPortletAssignable)
from zope.component import getUtility, getMultiAdapter, ComponentLookupError


class PloneHtmlProcessor(object):
    def __init__(self, handler, dry=False):
        self.handler = handler
        self.dry = dry

    def process(self, context, processed_portlets=None):
        if not context.getId().startswith('portal_'):
            if processed_portlets is None:
                processed_portlets = []
            if isinstance(context, base.ATCTContent):
                for info in self.process_content(context):
                    yield info
            # process portlets, both Plone ones and those from Collage
            for info in self.process_portlets(context, processed_portlets):
                yield info
            for item in context.objectValues():
                for info in self.process(item, processed_portlets):
                    yield info

    def process_portlets(self, context, processed_portlets):
        for manager_name in (
                'plone.leftcolumn', 'plone.rightcolumn',
                'collage.portletmanager'):
            try:
                manager = getUtility(IPortletManager, manager_name, context)
            except ComponentLookupError:
                continue
            if manager:
                retriever = getMultiAdapter(
                    (context, manager), IPortletRetriever)
                for portlet in retriever.getPortlets():
                    assignment = portlet['assignment']
                    if assignment in processed_portlets:
                        continue
                    processed_portlets.append(assignment)
                    if hasattr(assignment, 'text'):
                        html = assignment.text
                        html, results, fixed = self.handler(html, context)
                        for info in results:
                            yield (context, portlet, info)
                        if fixed and not self.dry:
                            assignment.text = html
                            assignment._p_changed = True

    def process_content(self, context):
        fields = context.schema.fields()
        for field in fields:
            if (field.type != 'text' or
                    field.default_output_type != 'text/x-html-safe'):
                continue
            fieldname = field.getName()
            html = field.getRaw(context)
            html, results, fixed = self.handler(html, context)
            for info in results:
                yield (context, field, info)
            if fixed and not self.dry:
                field.set(context, html)
