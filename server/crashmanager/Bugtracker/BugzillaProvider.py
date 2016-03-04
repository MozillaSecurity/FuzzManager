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

import base64
from datetime import datetime
from django.forms.models import model_to_dict
from django.shortcuts import render, get_object_or_404
import json
import os
import re
import requests

from crashmanager.Bugtracker.Provider import Provider
from crashmanager.models import BugzillaTemplate, User


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
            (user, created) = User.objects.get_or_create(user=request.user)

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
                attachmentData['testcase_attach'] = True
            else:
                crashEntry.testcase.test.open(mode='r')
                testcase_data = crashEntry.testcase.test.read()
                crashEntry.testcase.test.close()

                # If the file is too large, also attach it, even if plaintext
                if len(testcase_data) <= 2048:
                    sdata['testcase'] = testcase_data
                else:
                    sdata['testcase'] = "See attachment."
                    attachmentData['testcase_attach'] = True

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
        for field in ["summary", "testcase", "crashdata", "shortsig", "product", "version", "args", "os", "platform"]:
            template["description"] = template["description"].replace('%%%s%%' % field, sdata[field])
            template["comment"] = template["comment"].replace('%%%s%%' % field, sdata[field])

        # Also process all metadata variables in our bug description and comment field
        def substituteMetadata(source, metadata):
            # Find all metadata variables requested for subtitution
            metadataVars = re.findall("%metadata\.([a-zA-Z0-9]+)%", source)
            for mVar in metadataVars:
                if not mVar in metadata:
                    metadata[mVar] = "(%s not available)" % mVar

                source = source.replace('%metadata.' + mVar + '%', metadata[mVar])
            return source
        template["description"] = substituteMetadata(template["description"], metadata)
        template["comment"] = substituteMetadata(template["comment"], metadata)

        # Handle ".attached" properties
        if '%crashdata.attached%' in template["description"] or '%crashdata.attached%' in template["comment"]:
            template["description"] = template["description"].replace('%crashdata.attached%', "For detailed crash information, see attachment.")
            template["comment"] = template["comment"].replace('%crashdata.attached%', "For detailed crash information, see attachment.")
            attachmentData["crashdata_attach"] = sdata['crashdata']

        # Remove the specified pathPrefix from traces and assertion
        if "pathPrefix" in metadata:
            template["summary"] = template["summary"].replace(metadata["pathPrefix"], "")
            template["description"] = template["description"].replace(metadata["pathPrefix"], "")
            template["comment"] = template["comment"].replace(metadata["pathPrefix"], "")

            if "crashdata_attach" in attachmentData:
                attachmentData["crashdata_attach"] = attachmentData["crashdata_attach"].replace(metadata["pathPrefix"], "")

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
                   'hostname' : self.hostname,
                   'templates' : templates,
                   'template' : template,
                   'entry' : crashEntry,
                   'provider' : self.pk,
                   'mode' : mode,
                   'postTarget' : postTarget,
                   'attachmentData' : attachmentData,
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
            crashdata_attach = request.POST['crashdata_attach']

        testcase_attach = False
        if 'testcase_attach' in request.POST:
            testcase_attach = True

        # Remove any other variables that we don't want to pass on
        for key in request.POST:
            if not key in self.templateFields:
                del(args[key])

        # Convert the attrs field to a dict
        if "attrs" in args:
            args["attrs"] = dict([x.split("=", 1) for x in args["attrs"].splitlines()])

        if 'security' in request.POST and request.POST['security']:
            args["groups"] = ["core-security"]
            # Allow security_group to override the default security group used
            if 'security_group' in request.POST and request.POST['security_group']:
                args["groups"] = [ request.POST['security_group'] ]

        # security_group is a field we need in our template, but it does not correspond
        # to a field in Bugzilla so we need to remove it here.
        if 'security_group' in args:
            del(args['security_group'])

        # Create the bug
        bz = BugzillaREST(self.hostname, username, password, api_key)
        ret = bz.createBug(**args)
        if not "id" in ret:
            raise RuntimeError("Failed to create bug: %s", ret)

        # If we were told to attach the crash data, do so now
        if crashdata_attach:
            cRet = bz.addAttachment(ret["id"], crashdata_attach, "crash_data.txt", "Detailed Crash Information", is_binary=False)
            ret["crashdataAttachmentResponse"] = cRet

        # If we have a binary testcase or the testcase is too large,
        # attach it here in a second step
        if crashEntry.testcase != None:
            crashEntry.testcase.test.open(mode='rb')
            data = crashEntry.testcase.test.read()
            crashEntry.testcase.test.close()
            filename = os.path.basename(crashEntry.testcase.test.name)

            if args['testcase_filename']:
                filename = args['testcase_filename']

            if crashEntry.testcase.isBinary:
                aRet = bz.addAttachment(ret["id"], data, filename, "Testcase", is_binary=True)
                ret["attachmentResponse"] = aRet
            elif len(data) > 2048 or testcase_attach:
                aRet = bz.addAttachment(ret["id"], data, filename, "Testcase", is_binary=False)
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

        bz = BugzillaREST(self.hostname, username, password, api_key)

        ret = bz.createComment(**args)
        if not "id" in ret:
            raise RuntimeError("Failed to create comment: %s", ret)

        if 'callStackAsAttachment' in ret:
            cRet = bz.addAttachment(ret["id"], ret['callStackAsAttachment'], "call_stack.txt", "Call Stack for comment %s" % ret["id"], is_binary=False)
            ret["callStackAttachmentResponse"] = cRet

        # If we have a binary testcase or the testcase is too large,
        # attach it here in a second step
        if crashEntry.testcase != None:
            crashEntry.testcase.test.open(mode='rb')
            data = crashEntry.testcase.test.read()
            crashEntry.testcase.test.close()
            filename = os.path.basename(crashEntry.testcase.test.name)

            if crashEntry.testcase.isBinary:
                aRet = bz.addAttachment(args["id"], data, filename, "Testcase for comment %s" % ret["id"], is_binary=True)
                ret["attachmentResponse"] = aRet
            elif len(data) > 2048:
                aRet = bz.addAttachment(args["id"], data, filename, "Testcase for comment %s" % ret["id"], is_binary=False)
                ret["attachmentResponse"] = aRet

        return ret["id"]

    def renderContextCreateTemplate(self, request):
        if 'template' in request.GET:
            template = get_object_or_404(BugzillaTemplate, pk=request.GET['template'])
        else:
            template = {}

        data = {
                'createTemplate' : True,
                'template' : template,
                'provider' : self.pk,
                'mode' : "create",
                }

        return render(request, 'bugzilla/submit.html', data)

    def renderContextViewTemplate(self, request, templateId, mode):
        template = get_object_or_404(BugzillaTemplate, pk=templateId)
        templates = BugzillaTemplate.objects.all()

        data = {
                'provider' : self.pk,
                'templates' : templates,
                'template' : template,
                'mode' : mode,
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
                ret[bugId] = datetime.strptime(bugs[bugId]["cf_last_resolved"], "%Y-%m-%dT%H:%M:%SZ")

        return ret


class BugzillaREST():
    def __init__(self, hostname, username=None, password=None, api_key=None):
        self.hostname = hostname
        self.baseUrl = 'https://%s/rest' % self.hostname
        self.username = username
        self.password = password
        self.api_key = api_key
        self.authToken = None

        # The field to submit authentication information in depends on which
        # method we use (username/password means we need to use token, with
        # API key we can use the api_key field directly).
        self.authField = 'token'
        if self.api_key != None:
            self.authField = 'api_key'

    def login(self, forceLogin=False):
        if (self.username == None or self.password == None) and self.api_key == None:
            if forceLogin:
                raise RuntimeError("Need username/password or API key to login.")
            else:
                return False

        if forceLogin:
            self.authToken = None

        if self.api_key != None:
            self.authToken = self.api_key

        # We either use an API key which doesn't require any prior login
        # or we still have a valid authentication token that we can use.
        if self.authToken != None:
            return True

        loginUrl = "%s/login?login=%s&password=%s" % (self.baseUrl, self.username, self.password)
        response = requests.get(loginUrl)
        json = response.json()

        if not 'token' in json:
            raise RuntimeError('Login failed: %s', response.text)

        self.authToken = json["token"]
        return True

    def getBug(self, bugId):
        bugs = self.getBugs([ bugId ])

        if not bugs:
            return None

        return bugs[int(bugId)]

    def getBugStatus(self, bugIds):
        return self.getBugs(bugIds, include_fields=[ "id", "is_open", "resolution", "dupe_of", "cf_last_resolved" ])

    def getBugs(self, bugIds, include_fields=None, exclude_fields=None):
        if not isinstance(bugIds, list):
            bugIds = [ bugIds ]

        bugUrl = "%s/bug?id=%s" % (self.baseUrl, ",".join(bugIds))

        extraParams = []

        if self.login():
            extraParams.append("&%s=%s" % (self.authField, self.authToken))

        if include_fields:
            extraParams.append("&include_fields=%s" % ",".join(include_fields))

        if exclude_fields:
            extraParams.append("&exclude_fields=%s" % ",".join(exclude_fields))

        response = requests.get(bugUrl + "".join(extraParams))
        json = response.json()

        if not "bugs" in json:
            return None

        ret = {}
        for bug in json["bugs"]:
            ret[bug["id"]] = bug

        return ret

    def createBug(self, product, component, summary, version, description=None, op_sys=None,
                  platform=None, priority=None, severity=None, alias=None,
                  cc=None, assigned_to=None, comment_is_private=None, is_markdown=None,
                  groups=None, qa_contact=None, status=None, resolution=None,
                  target_milestone=None, flags=None, whiteboard=None, keywords=None, attrs=None):

        # Compose our bug attribute using all given arguments with special
        # handling of the self and attrs arguments
        l = locals()
        bug = {}
        for k in l:
            if k == "attrs" and l[k] != None:
                for ak in l[k]:
                    bug[ak] = l[k][ak]
            elif l[k] != None and l[k] != '' and k != "self":
                bug[k] = l[k]

        # Ensure we're logged in
        self.login()

        createUrl = "%s/bug?%s=%s" % (self.baseUrl, self.authField, self.authToken)
        response = requests.post(createUrl, bug)
        return response.json()

    def createComment(self, id, comment, is_private=False):
        if is_private:
            is_private = 1
        else:
            is_private = 0
        cobj = {}
        cobj["comment"] = comment
        cobj["is_private"] = is_private

        # Ensure we're logged in
        self.login()

        createUrl = "%s/bug/%s/comment?%s=%s" % (self.baseUrl, id, self.authField, self.authToken)
        response = requests.post(createUrl, cobj)
        return response.json()

    def addAttachment(self, ids, data, file_name, summary, comment=None, is_private=None, is_binary=False):
        # Compose our request using all given arguments with special
        # handling of the self and is_binary arguments
        l = locals()
        attachment = {}
        for k in l:
            if l[k] != None and l[k] != '' and k != "self" and k != "is_binary":
                attachment[k] = l[k]

        # Set proper content-type
        if is_binary:
            attachment["content_type"] = "application/octet-stream"
        else:
            attachment["content_type"] = "text/plain"

        # Attachment data must always be base64 encoded
        attachment["data"] = base64.b64encode(attachment["data"])

        # Ensure we're logged in
        self.login()

        attachUrl = "%s/bug/%s/attachment?%s=%s" % (self.baseUrl, ids, self.authField, self.authToken)
        response = requests.post(attachUrl, attachment)
        return response.json()

