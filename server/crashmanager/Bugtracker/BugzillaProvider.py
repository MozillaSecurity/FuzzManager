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
from crashmanager.Bugtracker.Provider import Provider
import re
import requests
from django.shortcuts import render, get_object_or_404
from crashmanager.models import BugzillaTemplate
from django.forms.models import model_to_dict
import json

class BugzillaProvider(Provider):
    def __init__(self, pk, hostname):
        super(BugzillaProvider, self).__init__(pk, hostname)
        
        self.templateFields = [
                    "templateName",
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
                ]

    def renderContextCreate(self, request, crashEntry):
        if 'template' in request.GET:
            template = get_object_or_404(BugzillaTemplate, pk=request.GET['template'])
        else:
            template = BugzillaTemplate.objects.filter(pk=1)
            
            if not template:
                template = {}
            else:
                template = model_to_dict(template[0])
        
        templates = BugzillaTemplate.objects.all()
        
        if template:
            # Load metadata that we need for various things
            metadata = {}
            if crashEntry.metadata:
                metadata =  json.loads(crashEntry.metadata)
            
            # Set the summary if empty
            if not template["summary"]:
                if crashEntry.shortSignature.startswith("[@"):
                    template["summary"] = "Crash %s" % crashEntry.shortSignature
                else:
                    template["summary"] = crashEntry.shortSignature
            
            # Determine the state of the testcase
            testcase = "(Test not available)"
            if crashEntry.testcase:
                if crashEntry.testcase.isBinary:
                    testcase = "See attachment."
                else:
                    crashEntry.testcase.test.open(mode='r')
                    testcase = crashEntry.testcase.test.read()
                    crashEntry.testcase.test.close()
            
            # Substitute various variables in the description
            template["description"] = template["description"].replace('%testcase%', testcase)
            
            if crashEntry.rawCrashData:
                crashData = crashEntry.rawCrashData
            else:
                crashData = crashEntry.rawStderr
        
            template["description"] = template["description"].replace('%crashdata%', crashData)
            template["description"] = template["description"].replace('%shortsig%', crashEntry.shortSignature)
            
            version = crashEntry.product.version
            if not version:
                version = "(Version not available)"
            
            template["description"] = template["description"].replace('%product%', crashEntry.product.name)
            template["description"] = template["description"].replace('%version%', version)

            args = ""
            if crashEntry.args:
                args = " ".join(json.loads(crashEntry.args))

            template["description"] = template["description"].replace('%args%', args)

            # Find all metadata variables requested for subtitution
            metadataVars = re.findall("%metadata\.([a-zA-Z0-9]+)%", template["description"])
            for mVar in metadataVars:
                if not mVar in metadata:
                    metadata[mVar] = "(%s not available)" % mVar
                
                template["description"] = template["description"].replace('%metadata.' + mVar + '%', metadata[mVar])

            # Now try to guess platform/OS if empty

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
        
        data = {
                   'hostname' : self.hostname,
                   'templates' : templates,
                   'template' : template,
                   'entry' : crashEntry,
                   'provider' : self.pk,
                }
    
        return render(request, 'bugzilla/create.html', data)
    
    def handlePOSTCreate(self, request, crashEntry):
        args = request.POST.dict()
        
        username = request.POST['username']
        password = request.POST['password']
        
        # Remove any other variables that we don't want to pass on
        for key in request.POST:
            if not key in self.templateFields:
                del(args[key])
        
        # Convert the attrs field to a dict
        if "attrs" in args:
            args["attrs"] = dict([x.split("=") for x in args["attrs"].splitlines()])
        
        if request.POST['security']:
            args["groups"] = ["core-security"]
            
        bz = BugzillaREST(self.hostname, username, password)
        
        ret = bz.createBug(**args)
        if not "id" in ret:
            raise RuntimeError("Failed to create bug: %s", ret)
        
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
                }
    
        return render(request, 'bugzilla/create.html', data)
    
    def renderContextViewTemplate(self, request, templateId):
        template = get_object_or_404(BugzillaTemplate, pk=templateId)
        templates = BugzillaTemplate.objects.all()
        
        data = {
                'provider' : self.pk,
                'templates' : templates,
                'template' : template,
                }
    
        return render(request, 'bugzilla/viewEditTemplate.html', data)
    
    def handlePOSTCreateEditTemplate(self, request):
        if 'template' in request.POST:
            bugTemplate = get_object_or_404(BugzillaTemplate, pk=request.POST['template'])
        else:
            bugTemplate = BugzillaTemplate()
            
        for field in self.templateFields:
            setattr(bugTemplate, field, request.POST[field])
        
        bugTemplate.save()
        return bugTemplate.pk
    
    def getBugData(self, bugId, username, password):
        bz = BugzillaREST(self.hostname, username, password)
        return bz.getBug(bugId)



class BugzillaREST():
    def __init__(self, hostname, username=None, password=None):
        self.hostname = hostname 
        self.baseUrl = 'https://%s/rest' % self.hostname
        self.username = username
        self.password = password
        self.authToken = None
    
    def login(self, forceLogin=False):
        if self.username == None or self.password == None:
            raise RuntimeError("Need username/password to login.")
        
        if forceLogin:
            self.authToken = None
            
        if self.authToken != None:
            return   

        loginUrl = "%s/login?login=%s&password=%s" % (self.baseUrl, self.username, self.password)  
        response = requests.get(loginUrl)
        json = response.json()
        
        if not 'token' in json:
            raise RuntimeError('Login failed: %s', response.text)
        
        self.authToken = json["token"]
        
    def getBug(self, bugId):
        # Ensure we're logged in
        self.login()
        
        bugUrl = "%s/bug/%s?token=%s" % (self.baseUrl, bugId, self.authToken)
        response = requests.get(bugUrl)
        json = response.json()
        
        if not "bugs" in json:
            return None
        
        bugs = json["bugs"]
        
        if not bugs:
            return None
        
        return bugs[0]
    
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
        
        createUrl = "%s/bug?token=%s" % (self.baseUrl, self.authToken)
        response = requests.post(createUrl, bug)
        return response.json()
