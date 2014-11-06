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
import requests
from django.template.context import RequestContext
from django.shortcuts import render, get_object_or_404
from crashmanager.models import BugzillaTemplate

class BugzillaProvider(Provider):
    def __init__(self):
        super(BugzillaProvider, self).__init__()

    def renderContextCreate(self, request, crashEntry):
        if 'template' in request.GET:
            template = get_object_or_404(BugzillaTemplate, pk=request.GET['template'])
        else:
            template = BugzillaTemplate.objects.filter(pk=1)
            
            if not template:
                template = {}
        
        templates = BugzillaTemplate.objects.all()
        
        # TODO: Here we must populate the template further with data from
        # our crashEntry. That means, set the proper OS, substitute variables
        # in summary/description, etc.
        
        context = RequestContext(request, {
                                           'templates' : templates,
                                           'template' : template,
                                           'entry' : crashEntry,
                                           'provider' : None
                                       })
    
        return render(request, 'bugzilla_create.html', context)
    
    def handlePOSTCreate(self, request):
        hostname = request.pop('hostname')
        username = request.pop('username')
        password = request.pop('password')
        
        # TODO: Here we need to pull out cc, alias, groups and flags
        # and re-add them in their proper array form
        
        bz = BugzillaREST(hostname, username, password)
        
        ret = bz.createBug(**request)
        if not "id" in ret:
            raise RuntimeError("Failed to create bug: %s", ret)
        
        return ret["id"]


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
    
    def createBug(self, product, component, summary, version, description=None, op_sys=None, 
                  platform=None, priority=None, severity=None, alias=None, 
                  cc=None, assigned_to=None, comment_is_private=None, is_markdown=None,
                  groups=None, qa_contact=None, status=None, resolution=None,
                  target_milestone=None, flags=None, attrs=None):
        
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