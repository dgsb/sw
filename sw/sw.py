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
import shutil

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
    cfg = configparser.ConfigParser()
    if os.path.exists(args.config_file):
        cfg.read(args.config_file)

    section = cfg['general']
    if args.svn_server:
        section['svn_server'] = args.svn_server
    if args.svn_dir:
        section['svn_dir'] = args.svn_dir
    if args.repository:
        section['repository'] = args.repository

    with open(args.config_file, 'w') as f:
        cfg.write(f)


def getcfg(args):
    """Complete the command line parameter with the content of the
    configuration file"""
    cfg = configparser.ConfigParser()
    cfg.read(args.config_file)
    if 'general' not in cfg.sections():
        return args
    for i in cfg['general']:
        if not getattr(args, i):
            setattr(args, i, cfg['general'][i])
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


def ls_remote(args):
    ls_url = args.svn_server
    if args.subdir:
        ls_url = os.path.join(ls_url, args.subdir)
    res = sh.svn('ls', ls_url)
    print(res)


def add_branch(args):
    name = os.path.basename(args.branch_name)
    if name in get_git_svn_repositories(args):
        print("The branch is already tracked")
        return 1

    branch_url = os.path.join(args.svn_server, args.branch_name)
    repo_dir = os.path.join(args.git_svn_dir, name)
    if None == args.r:
        sh.git('svn', 'clone', branch_url, repo_dir)
    else:
        sh.git('svn', 'clone', '-r', str(args.r) + ':HEAD', branch_url, repo_dir)
    os.chdir(args.repository)
    sh.git('remote', 'add', name, repo_dir)
    sh.git('fetch', name)
    sh.git('branch', name, name + "/master")
    os.chdir(repo_dir)
    sh.git('remote', 'add', 'origin', args.repository)


def rm_branch(args):
    branches = [os.path.basename(i) for i in get_git_svn_repositories(args)]
    if args.branch_name not in branches:
        print('The branch ' + args.branch_name + ' is not currently tracked',
              file=sys.stderr)
        sys.exit(1)

    os.chdir(args.repository)
    sh.git('branch', '-D', args.branch_name)
    sh.git('remote', 'remove', args.branch_name)
    print("Removing " + os.path.join(args.git_svn_dir, args.branch_name))
    shutil.rmtree(os.path.join(args.git_svn_dir, args.branch_name))


def commit(args):
    os.chdir(args.repository)
    branches = [os.path.basename(i) for i in get_git_svn_repositories(args)]
    if args.dstbranch not in branches:
        print("Unknown svn branch: " + args.dstbranch)
        sys.exit(1)

    if not args.srcbranch:
        args.srcbranch = str(sh.git('rev-parse', '--abbrev-ref', 'HEAD')).strip()

    branches = [str(i).split()[1].split('/')[2] for i in sh.git('show-ref', '--heads')]
    if args.srcbranch not in branches:
        print("Unknwon git branch " + args.srcbranch)
        sys.exit(1)

    # Both branches exist, check the that the src branch is up to date
    # regarding the dest branch
    commits = sh.git('rev-list', args.srcbranch + '..' + args.dstbranch + '/master')
    commits = str(commits).strip()
    if len(commits.splitlines()) > 0:
        print("The source branch is not up to date: " + str(commits.splitlines()))
        sys.exit(1)

    # Check there is actually something to commit
    commits = sh.git('rev-list', args.dstbranch + "/master.." + args.srcbranch)
    commits = str(commits).strip()
    if len(commits.splitlines()) == 0:
        print("There is nothing to commit on branch " + args.srcbranch)
        sys.exit(1)

    os.chdir(os.path.join(args.git_svn_dir, args.dstbranch))
    sh.git('fetch', '--all')
    cur_branch = str(sh.git('rev-parse', '--abbrev-ref', 'HEAD')).strip()
    if cur_branch != "master":
        print("The current branch of the git-svn repositories is not master")
        sys.exit(1)

    sh.git('merge', '--ff-only', 'origin/' + args.srcbranch)
    if args.n:
        dcommits = sh.git('svn', 'dcommit', '-n')
    else:
        dcommits = sh.git('svn', 'dcommit')
        os.chdir(args.repository)
        sh.git('rebase', args.dstbranch + "/master", args.srcbranch)
    print("Commit on svn: " + str(dcommits))
 

def branch_to_git_svn_repo(branch_name):
    pass


def repo2branch(reponame):
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
        '--svn-server',
        help="The svn url which will be used as a prefix to svn branches")
    parser.add_argument(
        '-s', '--svn-dir',
        help='the directory where are stored the svn branches checkouts')
    parser.add_argument(
        '-g', '--git-svn-dir',
        help='The directory where are stored the git-svn repositories')
    parser.add_argument(
        '-r', '--repository',
        help='the main git repository')

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

    # List remote svn branches
    list_remote_parser = subparser.add_parser(
        'ls_remote',
        help='list remote svn branch from the servers')
    list_remote_parser.add_argument(
        'subdir',
        nargs='?',
        default=None,
        help="Optional subdirectory to browse")
    list_remote_parser.set_defaults(func=ls_remote)

    # Add a new svn branch to track through git-svn
    add_branch_parser = subparser.add_parser(
        'add_branch',
        help='Add a new svn branch to track')
    add_branch_parser.add_argument(
        'branch_name',
        help='The name of the svn branch to track')
    add_branch_parser.add_argument(
        '-r',
        default=None,
        type=int,
        help='The oldest revision to fetch on the branch')
    add_branch_parser.set_defaults(func=add_branch)

    # Remove a svn branch
    rm_branch_parser = subparser.add_parser(
        'rm_branch',
        help='Stop tracking a svn branch')
    rm_branch_parser.add_argument(
        'branch_name')
    rm_branch_parser.set_defaults(func=rm_branch)

    # Command for commiting the current git branch in svn
    commit_parser = subparser.add_parser(
        'commit',
        help='commit the current branch on the wanted svn branch')
    commit_parser.add_argument('-n', help='dry-run mode', action='store_true')
    commit_parser.add_argument(
        'dstbranch',
        help="The svn branch we want to commit on")
    commit_parser.add_argument(
        'srcbranch',
        nargs='?',
        default=None,
        help="The new content we want to commit on svn. By default it is the current branch")
    commit_parser.set_defaults(func=commit)

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

