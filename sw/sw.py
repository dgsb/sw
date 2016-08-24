#!/usr/bin/env python
# vim: ft=python:

import sys
import os
import os.path
import argparse
import configparser
import sh
import stat
import glob

cmdparser = None

def check_binary():
    """Ensure all needed binaries are available in the PATH"""
    binaries = ["git", "svn", "svnversion"]
    unavailable = []
    for i in binaries:
        try:
            sh.Command(i)
        except sh.CommandNotFound:
            unavailable.append(i)
    if len(unavailable) > 0:
        print("The following binaries are not available: " + str(unavailable))
        sys.exit(1)


def initcfg(args):
    if os.path.exists(args.config_file):
        print("The configuration file already exists")
        return 1

    cfg = configparser.ConfigParser()
    cfg['project'] = {
        'current_project': 'default'
    }
    cfg['default'] = {
        'git_dir': args.git_dir,
        'svn_dir': args.svn_dir,
        'repository': args.repository
    }
    with open(args.config_file, 'w') as f:
        cfg.write(f)


def switch_project(args):
    """This function changes the default current project which is stored in the
    configuration file"""
    cfg = configparse.ConfigParser()
    cfg.read(args.config_file)
    try:
        cur_project = cfg['project']['current_project']
    except:
        cur_project = None
    # No change needed, this is already the default current project
    if cur_project and cur_project == args.project_name:
        return
    if args.project_name not in cfg.keys():
        print("The project " + args.project_name + " does not exist")
        sys.exit(1)
    cfg['project']['current_project'] = args.project_name
    with open(args.config_file, 'w') as f:
        cfg.write(f)


def getcfg(args):
    """Complete the command line parameter with the content of the
    configuration file"""
    cfg = configparser.ConfigParser()
    cfg.read(args.config_file)
    
    # select the correct project
    cur_project = getattr(args, 'project')
    if not cur_project:
        try:
            cur_project = cfg['project']['current_project']
        except:
            pass
    if not cur_project:
        print("Can not identify the current project")
        sys.exit(1)

    if 'default' not in cfg.sections():
        return args
    for i in cfg['default']:
        if not getattr(args, i):
            setattr(args, i, cfg['default'][i])
    return args


def get_git_svn_repositories(args):
    """Returns the list of known svn repositories"""
    dirs = []
    for i in glob.glob(os.path.join(args.git_svn_dir, '*')):
        dirs.append(i)
    return dirs


def get_svn_repositories(args):
    """Return the list of known git-svn repositories"""
    dirs = []
    for i in glob.glob(os.path.join(args.svn_dir, '*')):
        dirs.append(i)
    return dirs


def update(args):
    """Update the known svn and git-svn repositories and fetch the data
    back in the main git repository"""
    for i in get_svn_repositories(args):
        os.chdir(i)
        sh.svn('update')
        version = sh.svnversion()
        print(str(i) + ': updated to "' + str(version).strip() + '"')
    for i in get_git_svn_repositories(args):
        os.chdir(i)
        sh.git('svn', 'fetch')
        sh.git('rebase', 'git-svn', 'master')
    os.chdir(args.repository)
    sh.git('fetch', '--all')


def list_branches(args):
    for i in sorted(get_git_svn_repositories(args)):
        print(os.path.basename(i))


def branch2repo(branch_name):
    pass


def repo2branch(reponame):
    pass


def commit(args):
    pass


def get_cmdline_parser():
    global cmdparser
    if cmdparser:
        return cmdparser

    # General options
    parser = argparse.ArgumentParser(description=
            "Svn Wrapper automatize the setup of a dual git/svn repository")
    parser.add_argument(
        '-c', '--config-file',
        default=os.path.join(os.environ["HOME"], '.swrc'))
    parser.add_argument(
        '-d', '--git-dir',
        help='the directory where to store the git objects for svn/git dual repositories')
    parser.add_argument(
        '-s', '--svn-dir',
        help='the directory where are stored the svn branches checkouts')
    parser.add_argument(
        '-g', '--git-svn-dir',
        help='The directory where are stored the git-svn repositories')
    parser.add_argument(
        '-r', '--repository',
        help='the main git repository')
    parser.add_argument(
        '--project',
        help='Context identifier for a workspace',
        default='default')

    subparser = parser.add_subparsers(dest='subcommand')

    # Command for setting the configuration file with general options
    initcfg_parser = subparser.add_parser(
        'initcfg',
        help='Initialize the configuration file')
    initcfg_parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Force the overwrite of the config file')
    initcfg_parser.set_defaults(func=initcfg)

    # Command for adding a new project with its set of repositories
    add_project_parser = subparser.add_parser(
        'add_project',
        help='Add configuration value for a new project')
    add_project_parser.add_argument(
        'project-name',
        help='The name of the project')
    add_project_parser.add_argument(
        'git-dir',
        help='The directory where the main git repository will be stored')
    add_project_parser.add_argument(
        'svn-dir',
        help='The directory where the per branch svn repositories will be stored')
    add_project_parser.add_argument(
        'git-svn-dir',
        help='The directory where the per branch git-svn repositories will be stored')

    # Command for changing the current project
    switch_project_parser = subparser.add_parser(
        'switch_project',
        help="Change the default current project")
    switch_project_parser.add_argument(
        'project-name',
        help="The name of the new default project")
    switch_project_parser.set_defaults(func=switch_project)

    # Command for updating the svn repositories
    update_parser = subparser.add_parser(
        'update',
        help='Update all svn repositories')
    update_parser.set_defaults(func=update)

    # Command for listing the known svn branches
    list_parser = subparser.add_parser(
        'list',
        help='List all known and commitable branches')
    list_parser.set_defaults(func=list_branches)

    # Command for commiting the current git branch in svn
    commit_parser = subparser.add_parser(
        'commit',
        help='commit the current branch on the wanted svn branch'
    )
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument(
        'destbranch',
        help="The svn branch we want to commit on")

    cmdparser = parser
    return cmdparser
    

def main():
    args = get_cmdline_parser().parse_args()
    if hasattr(args, "func"):
        func = args.func
    else:
        func = None
    # update args missing from the command line with
    # the one from the configuration file
    if (not func) or (func != initcfg):
        args = getcfg(args)

    if func:
        sys.exit(func(args))
    else:
        get_cmdline_parser().print_help()
        sys.exit(1)

if "__main__" == __name__:
    main()

