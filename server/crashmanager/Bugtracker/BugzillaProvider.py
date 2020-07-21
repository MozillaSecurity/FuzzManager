'''
Bugzilla Bug Provider Interface

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

import json
import os
import re

from django.forms.models import model_to_dict
from django.shortcuts import render, get_object_or_404
from django.utils import dateparse

from .BugzillaREST import BugzillaREST
from .Provider import Provider
from ..models import BugzillaTemplate, User


class BugzillaProvider(Provider):
    def __init__(self, pk, hostname):
        super(BugzillaProvider, self).__init__(pk, hostname)

        self.templateFields = [
            "name",
            "product",
            "component",
            "summary",
            "version",
            "description",
            "op_sys",
            "platform",
            "priority",
            "severity",
            "alias",
            "cc",
            "assigned_to",
            "qa_contact",
            "target_milestone",
            "whiteboard",
            "keywords",
            "attrs",
            "security_group",
            "testcase_filename",
        ]

        self.templateFlags = [
            "security",
        ]

    def getTemplateForUser(self, request, crashEntry):
        if 'template' in request.GET:
            obj = get_object_or_404(BugzillaTemplate, pk=request.GET['template'])
            template = model_to_dict(obj)
            template["pk"] = obj.pk
        else:
            user = User.get_or_create_restricted(request.user)[0]

            obj = BugzillaTemplate.objects.filter(name__contains=crashEntry.tool.name)
            if not obj:
                defaultTemplateId = user.defaultTemplateId
                if not defaultTemplateId:
                    defaultTemplateId = 1

                obj = BugzillaTemplate.objects.filter(pk=defaultTemplateId)

            if not obj:
                template = {}
            else:
                template = model_to_dict(obj[0])
                template["pk"] = obj[0].pk

        return template

    def substituteTemplateForCrash(self, template, crashEntry):
        # Store substitution data here for later
        sdata = {}

        # Store possible attachment data/flags (e.g. crashdata)
        attachmentData = {}

        # For now, the skip test checkbox isn't part of the template
        attachmentData['testcase_skip'] = False

        # Load metadata that we need for various things
        metadata = {}
        if crashEntry.metadata:
            metadata = json.loads(crashEntry.metadata)

        # Set the summary if empty
        if not template["summary"]:
            if crashEntry.shortSignature.startswith("[@"):
                template["summary"] = "Crash %s" % crashEntry.shortSignature
            else:
                template["summary"] = crashEntry.shortSignature

        sdata["summary"] = template["summary"]

        # Determine the state of the testcase
        sdata['testcase'] = "(Test not available)"
        if crashEntry.testcase:
            if crashEntry.testcase.isBinary:
                sdata['testcase'] = "See attachment."
            else:
                crashEntry.testcase.test.open(mode='rb')
                testcase_data = crashEntry.testcase.test.read()
                crashEntry.testcase.test.close()

                def is_ascii(data):
                    try:
                        data.decode('ascii')
                        return True
                    except UnicodeDecodeError:
                        return False

                # If the file is too large, also attach it, even if plaintext.
                # Also attach if the file can't be decoded as ascii, as some bug
                # tracking systems might have trouble with unicode comment data.
                if len(testcase_data) <= 2048 and is_ascii(testcase_data):
                    sdata['testcase'] = testcase_data.decode('ascii')
                else:
                    sdata['testcase'] = "See attachment."

        if crashEntry.rawCrashData:
            sdata['crashdata'] = crashEntry.rawCrashData
        else:
            sdata['crashdata'] = crashEntry.rawStderr

        sdata['shortsig'] = crashEntry.shortSignature

        sdata['version'] = crashEntry.product.version
        if not sdata['version']:
            sdata['version'] = "(Version not available)"

        sdata['product'] = crashEntry.product.name
        sdata['os'] = crashEntry.os.name
        sdata['platform'] = crashEntry.platform.name
        sdata['client'] = crashEntry.client.name

        sdata['args'] = ""
        if crashEntry.args:
            sdata['args'] = " ".join(json.loads(crashEntry.args))

        # Now try to guess platform/OS for Bugzilla if empty

        # FIXME: Maybe the best way would be to actually provide the OS as it is in the bugtracker
        if not template["op_sys"]:
            if crashEntry.os.name == "linux":
                template["op_sys"] = "Linux"
            elif crashEntry.os.name == "macosx":
                template["op_sys"] = "Mac OS X"
            elif crashEntry.os.name.startswith("win"):
                # Translate win7 -> Windows 7, win8 -> Windows 8
                # Doesn't work for Vista, XP, needs to be improved
                template["op_sys"] = crashEntry.os.name.replace("win", "Windows ")

        if not template["platform"]:
            # BMO uses x86_64, not x86-64, and ARM instead of arm
            template["platform"] = crashEntry.platform.name.replace('-', '_').replace('arm', 'ARM')

        # Process all support variables in our bug description and comment field
        for field in ["summary", "shortsig", "product", "version", "args", "os", "platform", "client"]:
            template["description"] = template["description"].replace('%%%s%%' % field, sdata[field])
            template["comment"] = template["comment"].replace('%%%s%%' % field, sdata[field])

        # Testcase and Crashdata need special handling when being inlined, due to potential markdown formatting
        for field in ["testcase", "crashdata"]:
            mdata = "\n".join(["    %s" % x for x in sdata[field].splitlines()])
            template["description"] = template["description"].replace('%%%s%%' % field, mdata)
            template["comment"] = template["comment"].replace('%%%s%%' % field, mdata)

        # Also process all metadata variables in our bug description and comment field
        def substituteMetadata(source, metadata):
            # Find all metadata variables requested for subtitution
            metadataVars = re.findall(r"%metadata\.([a-zA-Z0-9_-]+)%", source)
            for mVar in metadataVars:
                if mVar not in metadata:
                    metadata[mVar] = "(%s not available)" % mVar

                source = source.replace('%metadata.' + mVar + '%', metadata[mVar])
            return source
        template["description"] = substituteMetadata(template["description"], metadata)
        template["comment"] = substituteMetadata(template["comment"], metadata)
        template["attrs"] = substituteMetadata(template["attrs"], metadata)

        # Handle ".attached" properties
        if '%crashdata.attached%' in template["description"] or '%crashdata.attached%' in template["comment"]:
            template["description"] = template["description"].replace(
                '%crashdata.attached%', "For detailed crash information, see attachment.")
            template["comment"] = template["comment"].replace(
                '%crashdata.attached%', "For detailed crash information, see attachment.")
            attachmentData["crashdata_attach"] = sdata['crashdata']

        # Remove the specified pathPrefix from traces and assertion
        if "pathPrefix" in metadata:
            template["summary"] = template["summary"].replace(metadata["pathPrefix"], "")
            template["description"] = template["description"].replace(metadata["pathPrefix"], "")
            template["comment"] = template["comment"].replace(metadata["pathPrefix"], "")

            if "crashdata_attach" in attachmentData:
                attachmentData["crashdata_attach"] = attachmentData["crashdata_attach"].replace(
                    metadata["pathPrefix"], "")

        if crashEntry.shortSignature.startswith("[@"):
            template["attrs"] = template["attrs"] + "\ncf_crash_signature=" + crashEntry.shortSignature

        return attachmentData

    def renderContextGeneric(self, request, crashEntry, mode, postTarget):
        # This generic function works for both creating bugs and commenting
        # because they require almost the same actions
        template = self.getTemplateForUser(request, crashEntry)
        templates = BugzillaTemplate.objects.all()

        attachmentData = {}

        if template:
            attachmentData = self.substituteTemplateForCrash(template, crashEntry)

        data = {
            'hostname': self.hostname,
            'templates': templates,
            'template': template,
            'entry': crashEntry,
            'provider': self.pk,
            'mode': mode,
            'postTarget': postTarget,
            'attachmentData': attachmentData,
        }

        return render(request, 'bugzilla/submit.html', data)

    def renderContextCreate(self, request, crashEntry):
        return self.renderContextGeneric(request, crashEntry, "create", "createbug")

    def renderContextComment(self, request, crashEntry):
        return self.renderContextGeneric(request, crashEntry, "comment", "createbugcomment")

    def handlePOSTCreate(self, request, crashEntry):
        args = request.POST.dict()

        username = request.POST['bugzilla_username']
        password = request.POST['bugzilla_password']
        api_key = None

        # If we have no username, interpret the password as API key
        if not username:
            api_key = password
            password = None

        # Fiddle out attachment data/flags before POST conversion
        # because they are not template fields and would be stripped
        crashdata_attach = None
        if 'crashdata_attach' in request.POST:
            crashdata_attach = request.POST['crashdata_attach'].encode('utf-8')

        # Remove any other variables that we don't want to pass on
        for key in request.POST:
            if key not in self.templateFields:
                del(args[key])

        # Convert the attrs field to a dict
        if "attrs" in args:
            args["attrs"] = dict([x.split("=", 1) for x in args["attrs"].splitlines()])

        if 'security' in request.POST and request.POST['security']:
            args["groups"] = ["core-security"]
            # Allow security_group to override the default security group used
            if 'security_group' in request.POST and request.POST['security_group']:
                args["groups"] = [request.POST['security_group']]

        # security_group is a field we need in our template, but it does not correspond
        # to a field in Bugzilla so we need to remove it here.
        if 'security_group' in args:
            del(args['security_group'])

        # Strip the submitted testcase filename, we need to handle
        # it separately when creating our testcase attachment
        submitted_testcase_filename = None
        if 'testcase_filename' in args:
            submitted_testcase_filename = args['testcase_filename']
            del(args['testcase_filename'])

        # Create the bug
        bz = BugzillaREST(self.hostname, username, password, api_key)
        ret = bz.createBug(**args)
        if "id" not in ret:
            raise RuntimeError("Failed to create bug: %s", ret)

        # If we were told to attach the crash data, do so now
        if crashdata_attach:
            cRet = bz.addAttachment(ret["id"], crashdata_attach, "crash_data.txt", "Detailed Crash Information",
                                    is_binary=False)
            ret["crashdataAttachmentResponse"] = cRet

        # If we have a binary testcase or the testcase is too large,
        # attach it here in a second step
        if crashEntry.testcase is not None and 'testcase_skip' not in request.POST:
            crashEntry.testcase.test.open(mode='rb')
            data = crashEntry.testcase.test.read()
            crashEntry.testcase.test.close()
            filename = os.path.basename(crashEntry.testcase.test.name)

            if submitted_testcase_filename:
                filename = submitted_testcase_filename

            aRet = bz.addAttachment(ret["id"], data, filename, "Testcase",
                                    is_binary=crashEntry.testcase.isBinary)
            ret["attachmentResponse"] = aRet

        return ret["id"]

    def handlePOSTComment(self, request, crashEntry):
        args = {}
        args["id"] = request.POST["bug_id"]
        args["comment"] = request.POST["comment"]
        if 'is_private' in request.POST and request.POST['is_private']:
            args["is_private"] = True

        username = request.POST['bugzilla_username']
        password = request.POST['bugzilla_password']
        api_key = None

        # If we have no username, interpret the password as API key
        if not username:
            api_key = password
            password = None

        # Handle testcase filename separately if requested
        submitted_testcase_filename = None
        if 'testcase_filename' in request.POST:
            submitted_testcase_filename = request.POST['testcase_filename']

        crashdata_attach = None
        if 'crashdata_attach' in request.POST:
            crashdata_attach = request.POST['crashdata_attach'].encode('utf-8')

        bz = BugzillaREST(self.hostname, username, password, api_key)

        ret = bz.createComment(**args)
        if "id" not in ret:
            raise RuntimeError("Failed to create comment: %s", ret)

        # If we were told to attach the crash data, do so now
        if crashdata_attach:
            cRet = bz.addAttachment(args["id"], crashdata_attach, "crash_data.txt", "Detailed Crash Information",
                                    is_binary=False)
            ret["crashdataAttachmentResponse"] = cRet

        # If we have a binary testcase or the testcase is too large,
        # attach it here in a second step
        if crashEntry.testcase is not None and 'testcase_skip' not in request.POST:
            crashEntry.testcase.test.open(mode='rb')
            data = crashEntry.testcase.test.read()
            crashEntry.testcase.test.close()
            filename = os.path.basename(crashEntry.testcase.test.name)

            if submitted_testcase_filename:
                filename = submitted_testcase_filename

            # A bug in BMO is causing "count" to be missing.
            # This workaround ensures we can still attach the missing file.
            cref = "previous comment"
            if "count" in ret:
                cref = "comment %s" % ret["count"]

            aRet = bz.addAttachment(args["id"], data, filename, "Testcase for %s" % cref,
                                    is_binary=crashEntry.testcase.isBinary)
            ret["attachmentResponse"] = aRet

        return ret["id"]

    def renderContextCreateTemplate(self, request):
        if 'template' in request.GET:
            template = get_object_or_404(BugzillaTemplate, pk=request.GET['template'])
        else:
            template = {}

        data = {
            'hostname': self.hostname,
            'createTemplate': True,
            'template': template,
            'provider': self.pk,
            'mode': "create",
        }

        return render(request, 'bugzilla/submit.html', data)

    def renderContextViewTemplate(self, request, templateId, mode):
        template = get_object_or_404(BugzillaTemplate, pk=templateId)
        templates = BugzillaTemplate.objects.all()

        data = {
            'hostname': self.hostname,
            'provider': self.pk,
            'templates': templates,
            'template': template,
            'mode': mode,
        }

        return render(request, 'bugzilla/view_edit_template.html', data)

    def handlePOSTCreateEditTemplate(self, request):
        if 'template' in request.POST:
            bugTemplate = get_object_or_404(BugzillaTemplate, pk=request.POST['template'])
        else:
            bugTemplate = BugzillaTemplate()

        if "comment" in request.POST:
            # If we're updating the comment field of a template, then just update that field
            bugTemplate.comment = request.POST["comment"]
        else:
            for field in self.templateFields:
                setattr(bugTemplate, field, request.POST[field])

            for flag in self.templateFlags:
                setattr(bugTemplate, flag, flag in request.POST)

        bugTemplate.save()
        return bugTemplate.pk

    def getTemplateList(self):
        return BugzillaTemplate.objects.all()

    def getBugData(self, bugId, username=None, password=None, api_key=None):
        bz = BugzillaREST(self.hostname, username, password, api_key)
        return bz.getBug(bugId)

    def getBugStatus(self, bugIds, username=None, password=None, api_key=None):
        ret = {}
        bz = BugzillaREST(self.hostname, username, password, api_key)
        bugs = bz.getBugStatus(bugIds)

        for bugId in bugs:
            if bugs[bugId]["is_open"]:
                ret[bugId] = None
            elif bugs[bugId]["dupe_of"]:
                ret[bugId] = str(bugs[bugId]["dupe_of"])
            else:
                ret[bugId] = dateparse.parse_datetime(bugs[bugId]["cf_last_resolved"])

        return ret
