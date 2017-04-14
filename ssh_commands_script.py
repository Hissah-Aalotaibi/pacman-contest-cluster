#!/usr/bin/python

#  ----------------------------------------------------------------------------------------------------------------------
# Import standard stuff

import os
import sys
import datetime
import argparse
import json
from itertools import product

# ----------------------------------------------------------------------------------------------------------------------
# Verify all necessary packages are present

missing_packages = []
try:
    # Used to prompt the password without echoing
    from getpass import getpass
except:
    missing_packages.append('getpass')

try:
    # Used to establish ssh connections
    import paramiko
except:
    missing_packages.append('paramiko')

if missing_packages:
    print('Some packages are missing. Please, run `pip install %s`' % ' '.join(missing_packages))
    sys.exit(1)

# ----------------------------------------------------------------------------------------------------------------------
# Import class from helper module

from ssh_helper import RunCommand

# ----------------------------------------------------------------------------------------------------------------------
# Load settings either from config.json or from the command line

def load_settings():
    CONFIG_PATH = 'config.json'

    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            settings = json.load(f)
    else:
        settings = {}

    parser = argparse.ArgumentParser(
        description='This script is to run a tournament between teams of agents for the Pacman package developed by '
                    'John DeNero (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu) at UC Berkeley.\n'
                    '\n'
                    'After running the tournament, the script generates a report in HTML. The report is, optionally, '
                    'uploaded to a specified server via scp.\n'
                    '\n'
                    'The parameters are saved in config.json, so it is only necessary to pass them the first time or '
                    'if they have to be updated.')

    parser.add_argument(
        '--organizer',
        help='name of the organizer of the contest',
    )
    parser.add_argument(
        '--host',
        help='ssh host'
    )
    parser.add_argument(
        '--user',
        help='username'
    )
    parser.add_argument(
        '--output-path',
        help='output directory',
        default='www'
    )
    parser.add_argument(
        '--contest-code-name',
        help='code name for the contest; this is suggested to not contain spaces and be lower-case',
        default='contest_%s' % datetime.datetime.today().year
    )
    parser.add_argument(
        '--teams-root',
        help='directory containing the zip files of the teams',
        default='teams'
    )
    parser.add_argument(
        '--include-staff-team',
        help='if passed, the staff team will be included (it should sit in a directory called staff_name)',
        action='store_true'
    )
    args = vars(parser.parse_args())

    if args.organizer:
        settings['organizer'] = args.organizer
    if args.organizer:
        settings['host'] = args.host
    if args.organizer:
        settings['user'] = args.user
    if args.organizer:
        settings['output_path'] = args.output_path
    if args.organizer:
        settings['contest_code_name'] = args.contest_code_name
    if args.include_staff_team:
        settings['include_staff_team'] = args.include_staff_team
    if args.teams_root:
        settings['teams_root'] = args.teams_root


    missing_parameters = {'organizer', 'host', 'user', 'output_path', 'contest_code_name'} - set(settings.keys())
    if missing_parameters:
        print('Missing parameters: %s. Aborting.' % list(sorted(missing_parameters)))
        parser.print_help()
        sys.exit(1)

    with open(CONFIG_PATH, 'w') as f:
        json.load(f, settings)

    return settings

# ----------------------------------------------------------------------------------------------------------------------

def upload_files(date_str, settings):
    RESULTS_FOLDER = "results_%s" % date_str
    RESULTS_TAR = "results_%s.tar" % date_str
    RECORDED_GAMES_TAR = 'recorded_games_%s' % date_str

    print "tar cvf %s *recorded* *replay*" % RECORDED_GAMES_TAR
    os.chdir(RESULTS_FOLDER)
    os.system("tar cvf %s *recorded*  *replay*" % RECORDED_GAMES_TAR)
    os.chdir('..')
    os.system("tar cvf %s %s/*" % (RESULTS_TAR, RESULTS_FOLDER))

    destination = settings['output_path']

    # TODO change to use Python functions so that this can run on non-Unix systems
    print "tar cvf %s %s/*" % (RESULTS_TAR, RESULTS_FOLDER)
    os.system("cp %s %s" % (RESULTS_TAR, destination))
    os.system("tar xvf %s " % RESULTS_TAR)
    os.system("rm  -rf %s/%s" % (destination, RESULTS_FOLDER))
    # os.system( "chmod 755  %s/*" % RESULTS_FOLDER )
    # os.system( "chmod 755  %s" % RESULTS_FOLDER )
    os.system("mv %s %s/%s" % (RESULTS_FOLDER, destination, RESULTS_FOLDER))

    output = "<html><body><h1>Results Pacman %s Tournament by Date</h1>" % settings['organizer']
    for root, dirs, files in os.walk(destination):
        for d in dirs:
            output += "<a href=\"%s/%s/results.html\"> %s  </a> <br>" % (settings['results_web_page'], d, d)
    output += "<br></body></html>"
    print "%s/results.html" % destination
    print output
    out_stream = open("%s/results.html" % destination, "w")
    out_stream.writelines(output)
    out_stream.close()

    # <a href="http://ww2.cs.mu.oz.au/482/tournament/layouts.tar.bz2"> Layouts used. Each day 2 new layouts are used  </a> <br>


    print "%s  Uploaded!" % RESULTS_TAR


def parse_result(lines, n1, n2):
    """
    Parses the result log of a match.
    :param lines: an iterator of the lines of the result log
    :param n1: name of Red team
    :param n2: name of Blue team
    :return: a tuple containing score, winner, loser and a flag signalling whether there was a bug
    """
    score = 0
    winner = None
    loser = None
    bug = False
    t1_errors = 0
    t2_errors = 0
    for line in lines:
        if line.find("wins by") != -1:
            score = abs(int(line.split('wins by')[1].split('points')[0]))
            if line.find('Red') != -1:
                winner = n1
                loser = n2
            elif line.find('Blue') != -1:
                winner = n2
                loser = n1
        if line.find("The Blue team has returned at least ") != -1:
            score = abs(int(line.split('The Blue team has returned at least ')[1].split(' ')[0]))
            winner = n2
            loser = n1
        elif line.find("The Red team has returned at least ") != -1:
            score = abs(int(line.split('The Red team has returned at least ')[1].split(' ')[0]))
            winner = n1
            loser = n2
        elif line.find("Tie Game") != -1:
            winner = None
            loser = None
        elif line.find("agent crashed") != -1:
            bug = True
            if line.find("Red agent crashed") != -1:
                t1_errors += 1
            if line.find("Blue agent crashed") != -1:
                t2_errors += 1
    return score, winner, loser, bug, t1_errors, t2_errors


def generate_output(date_str, team_stats, games):
    # TODO fill documentation
    """
    Generates the output HTML of the report of the tournament
    :param date_str: 
    :param team_stats: 
    :param games: 
    :return: 
    """
    output = "<html><body><h1>Date Tournament %s </h1><br><table border=\"1\">" % date_str
    output += "<tr><th>Team</th><th>Points</th><th>Win</th><th>Tie</th><th>Lost</th><th>FAILED</th><th>Score Balance</th></tr>"
    for key, (points, wins, draws, loses, errors, sum_score) in sorted(team_stats.items(), key=lambda (k, v): v[0], reverse=True):
        output += "<tr><td align=\"center\">%s</td><td align=\"center\">%d</td><td align=\"center\">%d</td><td align=\"center\" >%d</td><td align=\"center\">%d</td><td align=\"center\" >%d</td><td align=\"center\" >%d</td></tr>" % (
        key, points, wins, draws, loses, errors, sum_score)
    output += "</table>"

    output += "<br><br> <h2>Games</h2><br><a href=\"recorded_games_%s.tar\">DOWNLOAD RECORDED GAMES!</a><br><table border=\"1\">" % date_str
    output += "<tr><th>Team1</th><th>Team2</th><th>Layout</th><th>Score</th><th>Winner</th></tr>"
    for (n1, n2, layout, score, winner) in games:
        output += "<tr><td align=\"center\">"
        if winner == n1:
            output += "<b>%s</b>" % n1
        else:
            output += "%s" % n1
        output += "</td><td align=\"center\">"
        if winner == n2:
            output += "<b>%s</b>" % n2
        else:
            output += "%s" % n2
        if score == 9999:
            output += "</td><td align=\"center\">%s</td><td align=\"center\" >--</td><td align=\"center\"><b>FAILED</b></td></tr>" % layout
        else:
            output += "</td><td align=\"center\">%s</td><td align=\"center\" >%d</td><td align=\"center\"><b>%s</b></td></tr>" % (layout, score, winner)

    output += "</table></body></html>"
    return output

if __name__ == '__main__':
    settings = load_settings()

    run = RunCommand()
    run.do_add_host("%s,%s,%s" % (settings['host'], settings['user'], getpass()))
    run.do_connect()

    date_str = datetime.date.today().isoformat()

    # Tar the submitted teams and download to local machine

    # CHANGE STORAGE2 FOR LOCAL     ###########run.do_run( "tar cvf teams_%s.tar  /storage2/beta/users/nlipovetzky/test_teams/* "%(today.year,today.month,today.day) )

    # run.do_run( "tar cvf teams_%s.tar  /local/submit/submit/COMP90054/2/* "%(today.year,today.month,today.day) )

    # run.do_get( "teams_%s.tar"%(today.year,today.month,today.day) )

    # os.system("rm -rf storage2/")
    # os.system("rm -rf local/")

    # os.system("tar xvf teams_%s.tar"%(today.year,today.month,today.day) )

    '''
    ' unzip each team, copy it to teams folder, retrieve TeamName and AgentFactory from each config.py file, 
    ' and copy ff to each team folder
    '''
    # Init teams environment
    teams = []
    os.system("rm -rf teams/")
    os.system("mkdir teams")

    # CHANGE STORAGE2 FOR LOCAL
    for team_zip in os.listdir(settings['teams_root']):
        full_path = os.path.join(settings['teams_root'], team_zip)
        if full_path.endswith(".zip"):
            # Unzip team in the teams folder
            os.system("cp -rf %s teams/." % full_path)
            print "cp -rf %s teams/." % full_path
            os.system("unzip teams/%s -d teams/" % team_zip)
            print "unzip teams/%s -d teams/" % team_zip
            os.system("rm teams/%s" % team_zip)
            print "rm teams/%s" % team_zip
            folder_name = team_zip.split[:-4]

            # Copy ff in the team directory
            if os.path.isfile("teams/%s/ff" % folder_name) is False:
                os.system("cp staff_team/ff teams/%s/." % folder_name)
                print "cp staff_team/ff teams/%s/." % folder_name

            team_name = os.path.basename(full_path)[:-4]
            agent_factory = 'teams/' + team_name + '/team.py'

            print "teams/%s/team.py" % team_name
            if os.path.isfile("teams/%s/team.py" % team_name) is False:
                print "team.py missing!"
                exit(1)

            teams.append((team_name, agent_factory))



    if settings['include_staff_team']:
        teams.append(("staff_team", "teams/staff_team/team.py"))
    os.system("cp  -rf staff_team teams/.")
    os.system("rm -rf %s/teams/" % settings['contest_code_name'])
    os.system("cp  -rf teams %s/." % settings['contest_code_name'])
    print "cp  -rf %s_tournament_scripts/teams %s/." % (settings['organizer'], settings['contest_code_name'])

    '''
    ' Move to folder where pacman code is located (assume) is at '..'
    ' prepare the folder for the results, logs and the html
    '''

    print "\n\n", teams, "\n\n"

    os.system("rm -rf results_%s" % date_str)
    os.system("mkdir results_%s" % date_str)

    if len(teams) <= 1:
        output = "<html><body><h1>Date Tournament %s <br> 0 Teams participated!!</h1>" % date_str
        output += "</body></html>"
        out_stream = open("results_%s/results.html" % date_str, "w")
        out_stream.writelines(output)
        out_stream.close()
        print "results_%s/results.html summary generated!" % date_str
        upload_files(date_str, settings)

        run.do_close()
        exit(0)

    ladder = {n: [] for n, _ in teams}
    games = []
    errors = {n: 0 for n, _ in teams}
    '''
    ' captureLayouts sets how many layouts are going to be used at the tournament
    ' steps is the length of each game
    ' the tournament plays each team twice against each other, once as red team, once as blue
    '''

    os.chdir(settings['contest_code_name'])

    print os.system('pwd')
    captureLayouts = 4
    steps = 1200
    #    captureLayouts = 4
    #    steps = 3000
    for red_team, blue_team in product(teams, teams):
        for g in xrange(1, captureLayouts):
            (n1, a1) = red_team
            (n2, a2) = blue_team
            print "game %s vs %s" % (n1, n2)
            print "python capture.py -r %s -b %s -l contest1%dCapture -i %d -q --record" % (a1, a2, g, steps)
            os.system("python capture.py -r %s -b %s -l contest1%dCapture -i %d -q --record > ../results_%s/%s_vs_%s_contest1%dCapture_recorded.log" % (
                a1, a2, g, steps, date_str, n1, n2, g))
            in_stream = open("../results_%s/%s_vs_%s_contest1%dCapture_recorded.log" % (date_str, n1, n2, g), "r")
            lines = in_stream.readlines()
            in_stream.close()

            score, winner, loser, bug, t1_errors, t2_errors = parse_result(lines, n1, n2)

            errors[n1] += t1_errors
            errors[n2] += t2_errors

            if winner is None and bug is False:
                ladder[n1].append(score)
                ladder[n2].append(score)
            elif bug is False:
                ladder[winner].append(score)
                ladder[loser].append(-score)

            os.system("mv replay* ../results_%s/%s_vs_%s_contest1%dCapture_replay" % (
            date_str, n1, n2, g))
            if bug is False:
                games.append((n1, n2, "contest1%dCapture" % g, score, winner))
            else:
                games.append((n1, n2, "contest1%dCapture" % g, 9999, winner))

    team_stats = dict()

    os.chdir('..')

    '''
    ' Compute ladder and create html with results
    '''
    for team, scores in ladder.iteritems():

        wins = 0
        draws = 0
        loses = 0
        sum_score = 0
        for s in scores:
            if s > 0:
                wins += 1
            elif s == 0:
                draws += 1
            else:
                loses += 1
            sum_score += s

        team_stats[team] = [((wins * 3) + draws), wins, draws, loses, errors[team], sum_score]

    output = generate_output(date_str, team_stats, games)
    print "results_%s/results.html summary generated!" % date_str

    out_stream = open("results_%s/results.html" % date_str, "w")
    out_stream.writelines(output)
    out_stream.close()


    # Upload files to server
    upload_files(date_str, settings)

    run.do_close()
