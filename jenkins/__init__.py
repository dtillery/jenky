#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2010, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# 'AS IS' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Authors:
# Ken Conley <kwc@willowgarage.com>
# James Page <james.page@canonical.com>
# Tully Foote <tfoote@willowgarage.com>
# Matthew Gertner <matthew.gertner@gmail.com>

'''
.. module:: jenkins
    :platform: Unix, Windows
    :synopsis: Python API to interact with Jenkins

See examples at :doc:`example`
'''

import base64
import json

import six
from six.moves.http_client import BadStatusLine
from six.moves.urllib.error import HTTPError
from six.moves.urllib.error import URLError
from six.moves.urllib.parse import quote, urlencode
from six.moves.urllib.request import Request, urlopen

LAUNCHER_SSH = 'hudson.plugins.sshslaves.SSHLauncher'
LAUNCHER_COMMAND = 'hudson.slaves.CommandLauncher'
LAUNCHER_JNLP = 'hudson.slaves.JNLPLauncher'
LAUNCHER_WINDOWS_SERVICE = 'hudson.os.windows.ManagedWindowsServiceLauncher'

DEFAULT_CONN_TIMEOUT = 120
INFO = 'api/json'
PLUGIN_INFO = 'pluginManager/api/json?depth=%(depth)s'
CRUMB_URL = 'crumbIssuer/api/json'
JOB_INFO = 'job/%(name)s/api/json?depth=%(depth)s'
JOB_NAME = 'job/%(name)s/api/json?tree=name'
Q_INFO = 'queue/api/json?depth=0'
CANCEL_QUEUE = 'queue/cancelItem?id=%(id)s'
CREATE_JOB = 'createItem?name=%(name)s'  # also post config.xml
CONFIG_JOB = 'job/%(name)s/config.xml'
DELETE_JOB = 'job/%(name)s/doDelete'
ENABLE_JOB = 'job/%(name)s/enable'
DISABLE_JOB = 'job/%(name)s/disable'
COPY_JOB = 'createItem?name=%(to_name)s&mode=copy&from=%(from_name)s'
RENAME_JOB = 'job/%(from_name)s/doRename?newName=%(to_name)s'
BUILD_JOB = 'job/%(name)s/build'
STOP_BUILD = 'job/%(name)s/%(number)s/stop'
BUILD_WITH_PARAMS_JOB = 'job/%(name)s/buildWithParameters'
BUILD_INFO = 'job/%(name)s/%(number)d/api/json?depth=%(depth)s'
BUILD_CONSOLE_OUTPUT = 'job/%(name)s/%(number)d/consoleText'

CREATE_NODE = 'computer/doCreateItem?%s'
DELETE_NODE = 'computer/%(name)s/doDelete'
NODE_INFO = 'computer/%(name)s/api/json?depth=%(depth)s'
NODE_TYPE = 'hudson.slaves.DumbSlave$DescriptorImpl'
TOGGLE_OFFLINE = 'computer/%(name)s/toggleOffline?offlineMessage=%(msg)s'
CONFIG_NODE = 'computer/%(name)s/config.xml'

# for testing only
EMPTY_CONFIG_XML = '''<?xml version='1.0' encoding='UTF-8'?>
<project>
  <keepDependencies>false</keepDependencies>
  <properties/>
  <scm class='jenkins.scm.NullSCM'/>
  <canRoam>true</canRoam>
  <disabled>false</disabled>
  <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
  <triggers class='vector'/>
  <concurrentBuild>false</concurrentBuild>
  <builders/>
  <publishers/>
  <buildWrappers/>
</project>'''

# for testing only
RECONFIG_XML = '''<?xml version='1.0' encoding='UTF-8'?>
<project>
  <keepDependencies>false</keepDependencies>
  <properties/>
  <scm class='jenkins.scm.NullSCM'/>
  <canRoam>true</canRoam>
  <disabled>false</disabled>
  <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
  <triggers class='vector'/>
  <concurrentBuild>false</concurrentBuild>
<builders>
    <jenkins.tasks.Shell>
      <command>export FOO=bar</command>
    </jenkins.tasks.Shell>
  </builders>
  <publishers/>
  <buildWrappers/>
</project>'''


class JenkinsException(Exception):
    '''General exception type for jenkins-API-related failures.'''
    pass


class NotFoundException(JenkinsException):
    '''A special exception to call out the case of receiving a 404.'''
    pass


def auth_headers(username, password):
    '''Simple implementation of HTTP Basic Authentication.

    Returns the 'Authentication' header value.
    '''
    auth = '%s:%s' % (username, password)
    if isinstance(auth, six.text_type):
        auth = auth.encode('utf-8')
    return b'Basic ' + base64.b64encode(auth)


class Jenkins(object):

    def __init__(self, url, username=None, password=None, timeout=DEFAULT_CONN_TIMEOUT):
        '''Create handle to Jenkins instance.

        All methods will raise :class:`JenkinsException` on failure.

        :param username: Server username, ``str``
        :param password: Server password, ``str``
        :param url: URL of Jenkins server, ``str``
        :param timeout: Server connection timeout (in seconds), ``int``
        '''
        if url[-1] == '/':
            self.server = url
        else:
            self.server = url + '/'
        if username is not None and password is not None:
            self.auth = auth_headers(username, password)
        else:
            self.auth = None
        self.crumb = None
        self.timeout = timeout

    def _get_encoded_params(self, params):
        for k, v in params.items():
            if k in ["name", "to_name", "from_name", "msg"]:
                params[k] = quote(v)
        return params

    def maybe_add_crumb(self, req):
        # We don't know yet whether we need a crumb
        if self.crumb is None:
            try:
                response = self.jenkins_open(Request(
                    self.server + CRUMB_URL), add_crumb=False)
            except NotFoundException:
                # Don't need crumbs
                self.crumb = False
            else:
                self.crumb = json.loads(response.decode('utf-8'))
        if self.crumb:
            req.add_header(self.crumb['crumbRequestField'], self.crumb['crumb'])

    def get_job_info(self, name, depth=0):
        '''Get job information dictionary.

        :param name: Job name, ``str``
        :param depth: JSON depth, ``int``
        :returns: dictionary of job information
        '''
        try:
            response = self.jenkins_open(Request(
                self.server + JOB_INFO % self._get_encoded_params(locals())))
            if response:
                return json.loads(response)
            else:
                raise JenkinsException('job[%s] does not exist' % name)
        except HTTPError:
            raise JenkinsException('job[%s] does not exist' % name)
        except ValueError:
            raise JenkinsException(
                "Could not parse JSON info for job[%s]" % name)

    def get_job_name(self, name):
        '''Return the name of a job using the API.

        That is roughly an identity method which can be used to quickly verify
        a job exist or is accessible without causing too much stress on the
        server side.

        :param name: Job name, ``str``
        :returns: Name of job or None
        '''
        try:
            response = self.jenkins_open(
                Request(self.server + JOB_NAME %
                        self._get_encoded_params(locals())))
        except NotFoundException:
            return None
        else:
            actual = json.loads(response)['name']
            if actual != name:
                raise JenkinsException(
                    'Jenkins returned an unexpected job name %s '
                    '(expected: %s)' % (actual, name))
            return actual

    def debug_job_info(self, job_name):
        '''Print out job info in more readable format.'''
        for k, v in self.get_job_info(job_name).items():
            print(k, v)

    def jenkins_open(self, req, add_crumb=True):
        '''Utility routine for opening an HTTP request to a Jenkins server.

        This should only be used to extends the :class:`Jenkins` API.
        '''
        try:
            if self.auth:
                req.add_header('Authorization', self.auth)
            if add_crumb:
                self.maybe_add_crumb(req)
            response = urlopen(req, timeout=self.timeout).read()
            return response
        except HTTPError as e:
            # Jenkins's funky authentication means its nigh impossible to
            # distinguish errors.
            if e.code in [401, 403, 500]:
                # six.moves.urllib.error.HTTPError provides a 'reason'
                # attribute for all python version except for ver 2.6
                # Falling back to HTTPError.msg since it contains the
                # same info as reason
                raise JenkinsException(
                    'Error in request. ' +
                    'Possibly authentication failed [%s]: %s' % (
                        e.code, e.msg)
                )
            elif e.code == 404:
                raise NotFoundException('Requested item could not be found')
        except URLError as e:
                raise JenkinsException('Error in request: %s' % (e.reason))

    def get_build_info(self, name, number, depth=0):
        '''Get build information dictionary.

        :param name: Job name, ``str``
        :param name: Build number, ``int``
        :param depth: JSON depth, ``int``
        :returns: dictionary of build information, ``dict``

        Example::

            >>> j = Jenkins()
            >>> next_build_number = j.get_job_info('build_name')['next_build_number']
            >>> output = j.build_job('build_name')
            >>> from time import sleep; sleep(10)
            >>> build_info = j.get_build_info('build_name', next_build_number)
            >>> print(build_info)
            {u'building': False, u'changeSet': {u'items': [{u'date': u'2011-12-19T18:01:52.540557Z', u'msg': u'test', u'revision': 66, u'user': u'unknown', u'paths': [{u'editType': u'edit', u'file': u'/branches/demo/index.html'}]}], u'kind': u'svn', u'revisions': [{u'module': u'http://eaas-svn01.i3.level3.com/eaas', u'revision': 66}]}, u'builtOn': u'', u'description': None, u'artifacts': [{u'relativePath': u'dist/eaas-87-2011-12-19_18-01-57.war', u'displayPath': u'eaas-87-2011-12-19_18-01-57.war', u'fileName': u'eaas-87-2011-12-19_18-01-57.war'}, {u'relativePath': u'dist/eaas-87-2011-12-19_18-01-57.war.zip', u'displayPath': u'eaas-87-2011-12-19_18-01-57.war.zip', u'fileName': u'eaas-87-2011-12-19_18-01-57.war.zip'}], u'timestamp': 1324317717000, u'number': 87, u'actions': [{u'parameters': [{u'name': u'SERVICE_NAME', u'value': u'eaas'}, {u'name': u'PROJECT_NAME', u'value': u'demo'}]}, {u'causes': [{u'userName': u'anonymous', u'shortDescription': u'Started by user anonymous'}]}, {}, {}, {}], u'id': u'2011-12-19_18-01-57', u'keepLog': False, u'url': u'http://eaas-jenkins01.i3.level3.com:9080/job/build_war/87/', u'culprits': [{u'absoluteUrl': u'http://eaas-jenkins01.i3.level3.com:9080/user/unknown', u'fullName': u'unknown'}], u'result': u'SUCCESS', u'duration': 8826, u'fullDisplayName': u'build_war #87'}
        '''
        try:
            response = self.jenkins_open(Request(
                self.server + BUILD_INFO % self._get_encoded_params(locals())))
            if response:
                return json.loads(response)
            else:
                raise JenkinsException('job[%s] number[%d] does not exist'
                                       % (name, number))
        except HTTPError:
            raise JenkinsException('job[%s] number[%d] does not exist'
                                   % (name, number))
        except ValueError:
            raise JenkinsException(
                'Could not parse JSON info for job[%s] number[%d]'
                % (name, number)
            )

    def get_queue_info(self):
        ''':returns: list of job dictionaries, ``[dict]``

        Example::
            >>> j = Jenkins()
            >>> queue_info = j.get_queue_info()
            >>> print(queue_info[0])
            {u'task': {u'url': u'http://your_url/job/my_job/', u'color': u'aborted_anime', u'name': u'my_job'}, u'stuck': False, u'actions': [{u'causes': [{u'shortDescription': u'Started by timer'}]}], u'buildable': False, u'params': u'', u'buildableStartMilliseconds': 1315087293316, u'why': u'Build #2,532 is already in progress (ETA:10 min)', u'blocked': True}
        '''
        return json.loads(self.jenkins_open(
            Request(self.server + Q_INFO)
        ))['items']

    def cancel_queue(self, id):
        '''Cancel a queued build.

        :param id: Jenkins job id number for the build, ``int``
        '''
        # Jenkins seems to always return a 404 when using this REST endpoint
        # https://issues.jenkins-ci.org/browse/JENKINS-21311
        try:
            self.jenkins_open(
                Request(self.server + CANCEL_QUEUE % locals(), '',
                        headers={'Referer': self.server}))
        except NotFoundException:
            # Exception is expected; cancel_queue() is a best-effort
            # mechanism, so ignore it
            pass

    def get_info(self):
        """Get information on this Master.

        This information includes job list and view information.

        :returns: dictionary of information about Master, ``dict``

        Example::

            >>> j = Jenkins()
            >>> info = j.get_info()
            >>> jobs = info['jobs']
            >>> print(jobs[0])
            {u'url': u'http://your_url_here/job/my_job/', u'color': u'blue',
            u'name': u'my_job'}

        """
        try:
            return json.loads(self.jenkins_open(
                Request(self.server + INFO)))
        except HTTPError:
            raise JenkinsException("Error communicating with server[%s]"
                                   % self.server)
        except BadStatusLine:
            raise JenkinsException("Error communicating with server[%s]"
                                   % self.server)
        except ValueError:
            raise JenkinsException("Could not parse JSON info for server[%s]"
                                   % self.server)

    def get_version(self):
        """Get the version of this Master.

        :returns: This master's version number ``str``

        Example::

            >>> j = Jenkins()
            >>> info = j.get_version()
            >>> print info
            >>> 1.541

        """
        try:
            request = Request(self.server)
            request.add_header('X-Jenkins', '0.0')
            response = urlopen(request, timeout=self.timeout)
            return response.info().getheader('X-Jenkins')
        except HTTPError:
            raise JenkinsException("Error communicating with server[%s]"
                                   % self.server)
        except BadStatusLine:
            raise JenkinsException("Error communicating with server[%s]"
                                   % self.server)

    def get_plugins_info(self, depth=2):
        """Get all installed plugins information on this Master.

        This method retrieves information about each plugin that is installed
        on master.

        :param depth: JSON depth, ``int``
        :returns: info on all plugins ``[dict]``

        Example::

            >>> j = Jenkins()
            >>> info = j.get_plugins_info()
            >>> print(info)
            [{u'backupVersion': None, u'version': u'0.0.4', u'deleted': False,
            u'supportsDynamicLoad': u'MAYBE', u'hasUpdate': True,
            u'enabled': True, u'pinned': False, u'downgradable': False,
            u'dependencies': [], u'url':
            u'http://wiki.jenkins-ci.org/display/JENKINS/Gearman+Plugin',
            u'longName': u'Gearman Plugin', u'active': True, u'shortName':
            u'gearman-plugin', u'bundled': False}, ..]

        """
        try:
            plugins_info = json.loads(self.jenkins_open(
                Request(self.server + PLUGIN_INFO % locals())))
            return plugins_info['plugins']
        except HTTPError:
            raise JenkinsException("Error communicating with server[%s]"
                                   % self.server)
        except BadStatusLine:
            raise JenkinsException("Error communicating with server[%s]"
                                   % self.server)
        except ValueError:
            raise JenkinsException("Could not parse JSON info for server[%s]"
                                   % self.server)

    def get_plugin_info(self, name, depth=2):
        """Get an installed plugin information on this Master.

        This method retrieves information about a speicifc plugin.
        The passed in plugin name (short or long) must be an exact match.

        :param name: Name (short or long) of plugin, ``str``
        :param depth: JSON depth, ``int``
        :returns: a specific plugin ``dict``

        Example::

            >>> j = Jenkins()
            >>> info = j.get_plugin_info("Gearman Plugin")
            >>> print(info)
            {u'backupVersion': None, u'version': u'0.0.4', u'deleted': False,
            u'supportsDynamicLoad': u'MAYBE', u'hasUpdate': True,
            u'enabled': True, u'pinned': False, u'downgradable': False,
            u'dependencies': [], u'url':
            u'http://wiki.jenkins-ci.org/display/JENKINS/Gearman+Plugin',
            u'longName': u'Gearman Plugin', u'active': True, u'shortName':
            u'gearman-plugin', u'bundled': False}

        """
        try:
            plugins_info = json.loads(self.jenkins_open(
                Request(self.server + PLUGIN_INFO % self._get_encoded_params(locals()))))
            for plugin in plugins_info['plugins']:
                if plugin['longName'] == name or plugin['shortName'] == name:
                    return plugin
        except HTTPError:
            raise JenkinsException("Error communicating with server[%s]"
                                   % self.server)
        except BadStatusLine:
            raise JenkinsException("Error communicating with server[%s]"
                                   % self.server)
        except ValueError:
            raise JenkinsException("Could not parse JSON info for server[%s]"
                                   % self.server)

    def get_jobs(self):
        """Get list of jobs running.

        Each job is a dictionary with 'name', 'url', and 'color' keys.

        :returns: list of jobs, ``[ { str: str} ]``
        """
        return self.get_info()['jobs']

    def copy_job(self, from_name, to_name):
        '''Copy a Jenkins job

        :param from_name: Name of Jenkins job to copy from, ``str``
        :param to_name: Name of Jenkins job to copy to, ``str``
        '''
        self.jenkins_open(Request(
            self.server + COPY_JOB % self._get_encoded_params(locals()), ''))
        self.assert_job_exists(to_name, 'create[%s] failed')

    def rename_job(self, from_name, to_name):
        '''Rename an existing Jenkins job

        :param from_name: Name of Jenkins job to rename, ``str``
        :param to_name: New Jenkins job name, ``str``
        '''
        self.jenkins_open(Request(
            self.server + RENAME_JOB % self._get_encoded_params(locals()), ''))
        self.assert_job_exists(to_name, 'rename[%s] failed')

    def delete_job(self, name):
        '''Delete Jenkins job permanently.

        :param name: Name of Jenkins job, ``str``
        '''
        self.jenkins_open(Request(
            self.server + DELETE_JOB % self._get_encoded_params(locals()), ''))
        if self.job_exists(name):
            raise JenkinsException('delete[%s] failed' % (name))

    def enable_job(self, name):
        '''Enable Jenkins job.

        :param name: Name of Jenkins job, ``str``
        '''
        self.jenkins_open(Request(
            self.server + ENABLE_JOB % self._get_encoded_params(locals()), ''))

    def disable_job(self, name):
        '''Disable Jenkins job.

        To re-enable, call :meth:`Jenkins.enable_job`.

        :param name: Name of Jenkins job, ``str``
        '''
        self.jenkins_open(Request(
            self.server + DISABLE_JOB % self._get_encoded_params(locals()), ''))

    def job_exists(self, name):
        '''Check whether a job exists

        :param name: Name of Jenkins job, ``str``
        :returns: ``True`` if Jenkins job exists
        '''
        if self.get_job_name(name) == name:
            return True

    def assert_job_exists(self, name,
                          exception_message='job[%s] does not exist'):
        '''Raise an exception if a job does not exist

        :param name: Name of Jenkins job, ``str``
        :param exception_message: Message to use for the exception. Formatted
                                  with ``name``
        :throws: :class:`JenkinsException` whenever the job does not exist
        '''
        if not self.job_exists(name):
            raise JenkinsException(exception_message % name)

    def create_job(self, name, config_xml):
        '''Create a new Jenkins job

        :param name: Name of Jenkins job, ``str``
        :param config_xml: config file text, ``str``
        '''
        if self.job_exists(name):
            raise JenkinsException('job[%s] already exists' % (name))

        headers = {'Content-Type': 'text/xml'}
        self.jenkins_open(Request(
            self.server + CREATE_JOB % self._get_encoded_params(locals()), config_xml, headers))
        self.assert_job_exists(name, 'create[%s] failed')

    def get_job_config(self, name):
        '''Get configuration of existing Jenkins job.

        :param name: Name of Jenkins job, ``str``
        :returns: job configuration (XML format)
        '''
        request = Request(self.server + CONFIG_JOB % self._get_encoded_params(locals()))
        return self.jenkins_open(request)

    def reconfig_job(self, name, config_xml):
        '''Change configuration of existing Jenkins job.

        To create a new job, see :meth:`Jenkins.create_job`.

        :param name: Name of Jenkins job, ``str``
        :param config_xml: New XML configuration, ``str``
        '''
        headers = {'Content-Type': 'text/xml'}
        reconfig_url = self.server + CONFIG_JOB % self._get_encoded_params(locals())
        self.jenkins_open(Request(reconfig_url, config_xml, headers))

    def build_job_url(self, name, parameters=None, token=None):
        '''Get URL to trigger build job.

        Authenticated setups may require configuring a token on the server
        side.

        :param parameters: parameters for job, or None., ``dict``
        :param token: (optional) token for building job, ``str``
        :returns: URL for building job
        '''
        if parameters:
            if token:
                parameters['token'] = token
            return (self.server + BUILD_WITH_PARAMS_JOB % self._get_encoded_params(locals()) +
                    '?' + urlencode(parameters))
        elif token:
            return (self.server + BUILD_JOB % self._get_encoded_params(locals()) +
                    '?' + urlencode({'token': token}))
        else:
            return self.server + BUILD_JOB % self._get_encoded_params(locals())

    def build_job(self, name, parameters=None, token=None):
        '''Trigger build job.

        :param name: name of job
        :param parameters: parameters for job, or ``None``, ``dict``
        :param token: Jenkins API token
        '''
        return self.jenkins_open(Request(
            self.build_job_url(name, parameters, token), ""))

    def stop_build(self, name, number):
        '''Stop a running Jenkins build.

        :param name: Name of Jenkins job, ``str``
        :param number: Jenkins build number for the job, ``int``
        '''
        self.jenkins_open(Request(self.server + STOP_BUILD % self._get_encoded_params(locals())))

    def get_node_info(self, name, depth=0):
        '''Get node information dictionary

        :param name: Node name, ``str``
        :param depth: JSON depth, ``int``
        :returns: Dictionary of node info, ``dict``
        '''
        try:
            response = self.jenkins_open(Request(
                self.server + NODE_INFO % self._get_encoded_params(locals())))
            if response:
                return json.loads(response)
            else:
                raise JenkinsException('node[%s] does not exist' % name)
        except HTTPError:
            raise JenkinsException('node[%s] does not exist' % name)
        except ValueError:
            raise JenkinsException("Could not parse JSON info for node[%s]"
                                   % name)

    def node_exists(self, name):
        '''Check whether a node exists

        :param name: Name of Jenkins node, ``str``
        :returns: ``True`` if Jenkins node exists
        '''
        try:
            self.get_node_info(name)
            return True
        except JenkinsException:
            return False

    def assert_node_exists(self, name,
                           exception_message='node[%s] does not exist'):
        '''Raise an exception if a node does not exist

        :param name: Name of Jenkins node, ``str``
        :param exception_message: Message to use for the exception. Formatted
                                  with ``name``
        :throws: :class:`JenkinsException` whenever the node does not exist
        '''
        if not self.node_exists(name):
            raise JenkinsException(exception_message % name)

    def delete_node(self, name):
        '''Delete Jenkins node permanently.

        :param name: Name of Jenkins node, ``str``
        '''
        self.get_node_info(name)
        self.jenkins_open(Request(
            self.server + DELETE_NODE % self._get_encoded_params(locals()), ''))
        if self.node_exists(name):
            raise JenkinsException('delete[%s] failed' % (name))

    def disable_node(self, name, msg=''):
        '''Disable a node

        :param name: Jenkins node name, ``str``
        :param msg: Offline message, ``str``
        '''
        info = self.get_node_info(name)
        if info['offline']:
            return
        self.jenkins_open(Request(
            self.server + TOGGLE_OFFLINE % self._get_encoded_params(locals()), ''))

    def enable_node(self, name):
        '''Enable a node

        :param name: Jenkins node name, ``str``
        '''
        info = self.get_node_info(name)
        if not info['offline']:
            return
        msg = ''
        self.jenkins_open(Request(
            self.server + TOGGLE_OFFLINE % self._get_encoded_params(locals()), ''))

    def create_node(self, name, numExecutors=2, nodeDescription=None,
                    remoteFS='/var/lib/jenkins', labels=None, exclusive=False,
                    launcher=LAUNCHER_COMMAND, launcher_params={}):
        '''Create a node

        :param name: name of node to create, ``str``
        :param numExecutors: number of executors for node, ``int``
        :param nodeDescription: Description of node, ``str``
        :param remoteFS: Remote filesystem location to use, ``str``
        :param labels: Labels to associate with node, ``str``
        :param exclusive: Use this node for tied jobs only, ``bool``
        :param launcher: The launch method for the slave, ``jenkins.LAUNCHER_COMMAND``, ``jenkins.LAUNCHER_SSH``, ``jenkins.LAUNCHER_JNLP``, ``jenkins.LAUNCHER_WINDOWS_SERVICE``
        :param launcher_params: Additional parameters for the launcher, ``dict``
        '''
        if self.node_exists(name):
            raise JenkinsException('node[%s] already exists' % (name))

        mode = 'NORMAL'
        if exclusive:
            mode = 'EXCLUSIVE'

        launcher_params['stapler-class'] = launcher

        inner_params = {
            'name': name,
            'nodeDescription': nodeDescription,
            'numExecutors': numExecutors,
            'remoteFS': remoteFS,
            'labelString': labels,
            'mode': mode,
            'type': NODE_TYPE,
            'retentionStrategy': {
                'stapler-class':
                'hudson.slaves.RetentionStrategy$Always'
            },
            'nodeProperties': {'stapler-class-bag': 'true'},
            'launcher': launcher_params
        }

        params = {
            'name': name,
            'type': NODE_TYPE,
            'json': json.dumps(inner_params)
        }

        self.jenkins_open(Request(
            self.server + CREATE_NODE % urlencode(params)))

        self.assert_node_exists(name, 'create[%s] failed')

    def get_node_config(self, name):
        '''Get the configuration for a node.

        :param name: Jenkins node name, ``str``
        '''
        get_config_url = self.server + CONFIG_NODE % self._get_encoded_params(locals())
        return self.jenkins_open(Request(get_config_url))

    def reconfig_node(self, name, config_xml):
        '''Change the configuration for an existing node.

        :param name: Jenkins node name, ``str``
        :param config_xml: New XML configuration, ``str``
        '''
        headers = {'Content-Type': 'text/xml'}
        reconfig_url = self.server + CONFIG_NODE % self._get_encoded_params(locals())
        self.jenkins_open(Request(reconfig_url, config_xml, headers))

    def get_build_console_output(self, name, number):
        '''Get build console text.

        :param name: Job name, ``str``
        :param name: Build number, ``int``
        :returns: Build console output,  ``str``
        '''
        try:
            response = self.jenkins_open(Request(
                self.server + BUILD_CONSOLE_OUTPUT % self._get_encoded_params(locals())))
            if response:
                return response
            else:
                raise JenkinsException('job[%s] number[%d] does not exist'
                                       % (name, number))
        except HTTPError:
            raise JenkinsException('job[%s] number[%d] does not exist'
                                   % (name, number))