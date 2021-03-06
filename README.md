# PACMAN CAPTURE THE FLAG - CONTEST SCRIPT

This system runs complex contests for the [UC Berkley Pacman Conquer the Flag](http://ai.berkeley.edu/contest.html) game.

Designed & developed for RMIT COSC1125/1127 AI course in 2017 by lecturer A/Prof. Sebastian Sardina (with programming support by Marco Tamassia), based on an original script from Dr. Nir Lipovetzky. Since then, the tool has been continuously improved and extended to fit RMIT COSC1125/1127 and UNIMELB COMP90054 AI course.

The system runs on Python 3.x. Currently used on Python 3.6.

**CONTACT:** Prof. Sebastian Sardina (ssardina@gmail.com) and Dr. Nir Lipovetzky (nirlipo@gmail.com)

Table of Contents
=================

- [OVERVIEW](#overview)
  * [Features](#features)
  * [Dependencies](#dependencies)
- [MAIN COMPONENTS](#main-components)
- [OVERVIEW OF MARKING PROCESS](#overview-of-marking-process)
- [EXAMPLE RUNS](#example-runs)
  * [Run a contest](#run-a-contest)
  * [Run contest only vs staff teams](#run-contest-only-vs-staff-teams)
  * [Resume partial contest](#resume-partial-contest)
  * [Re-run only some teams in a given contest](#re-run-only-some-teams-in-a-given-contest)
  * [Re-run only updated teams](re-run-only-updated-teams)
- [WEB PAGE GENERATION](#web-page-generation)
- [SCHEDULE COMPETITION](#schedule-competition)
  * [Test command to schedule](#test-command-to-schedule)
  * [Setting up cron](#setting-up-cron)
- [MODIFYING THE CONTEST GAME](#modifying-the-contest-game)
- [TROUBLESHOOTING](#troubleshooting)
- [SCREENSHOT](#screenshot)
- [LICENSE](#license)




Created by [gh-md-toc](https://github.com/ekalinin/github-markdown-toc)




----------------------

## OVERVIEW ##

This system runs a full Pacman Capture the Flag tournament among many teams using a _cluster of machines/CPUs_ (e.g., [Australia's NeCTAR](https://nectar.org.au/).

The contest script takes a set of teams, a set of machine workers in a cluster, and a tournament configuration (which layouts and how many steps per game), and runs games concurrently (one per worker) for every pair of teams and layouts (round-robin type of tournament), and produces files and html web page with the results. With `n` teams playing on `k` layouts there will be `(n(n-1) / 2)k` games. To deal with too many teams, the script can play teams against staff team systems only and also split teams into random sub-contests and run them in sequence.

The system contains two main scripts:

1. ``` pacman_contest_cluster.py``` is the main script to actually run a contest.
2. ```pacman_html_generator.py``` generates an HTML web page from existing data of already ran contests.


To see options available run: 

```bash
$ python3  pacman_contest_cluster.py -h
```

```bash
$ python3 pacman_html_generator.py --h
```


### Features ###

* Build `n` subcontests where teams are assigned randomly to one of them.
* Play teams only against staff teams.
* Runs multiple games at the same time by using a cluster of worker machines/CPUs.
    * option `--workers-file <json file>`
    * connection via ssh with tunneling support if needed.
* Able to use variable number of fixed layouts and randomly generated layouts.
    * options `--no-fixed-layouts` and `--no-random-layouts `
* Map individual student submissions to teams.
    * Via student-team mapping file; option `--team-names`
* Generate an HTML page with the contest result and full details, including links to replay files.
    * Ability to store replays and logs into [`https://transfer.sh`](https://transfer.sh) service to avoid filling local www space.
    * Ranking generation: 3 points per win; 1 point per tie. Failed games are loses. Ordered by: points first, no. of wins second, score points third.
* Handle latest submission per team, by sorting via timestamp recorded in file name.
* Can resume a partial ran contest or extend an existing contest.
* Automate tournament using a `driver.py` script and `cron`.
* Save options into a JSON file `config.json` for future runs using `--build-config-file` option.
    
    
### Dependencies

In **each machine in the cluster**:

* unzip & zip commands (to pack and unpack submissions and files for transfer)
    * `sudo apt-get install -y unzip zip vim`
* Python 3.x with standard libraries.
    * The original UC Pacman Contest ran under Python 2, but in this system it was ported to version 3.
* Set the SSH server to accept as many connections as you want to run concurrently. This is done by changing option `MaxStartups` in file `/etc/ssh/sshd_config`. By default `sshd` has up to 10 connections.
    * For example, set `MaxStartups 100:30:100` to accept up to 100 simultaneous connections. Remember to restart the ssh server: `sudo service sshd restart`
    * For more info on this, see issue [#26](https://github.com/AI4EDUC/pacman-contest-cluster/issues/26).
* Cluster should have all the Python and Unix packages to run the contest. For example, in the NeCTAR cluster:
                            
    ```bash
    sudo apt-get update
    sudo apt-get install python3-pip unzip vim
    sudo pip3 install setuptools
  
    wget https://raw.githubusercontent.com/AI4EDUC/pacman-contest-cluster/master/requirements.txt
    python -m pip install --user --upgrade pip
    sudo pip3 install -r requirements.txt
    ```
                        
    If you do not have root access you can use `pip install -r requirements.txt --user` to do a user install. Get [requirements.txt](requirements.txt) with wget.

* Many students benefit from the availability other tools, like [TensorFlow](https://www.tensorflow.org/), [scikit-learn](http://scikit-learn.org/), [neat-python](https://github.com/CodeReclaimers/neat-python): 
    * `pip3 install tensorflow sklearn sklearn scipy neat-python --user` or `sudo pip install tensorflow sklearn scipy neat-python`
* If students want to use planners to solve pacman PDDL models for their solutions, copy any planner to `/usr/local/bin`. For example, in the NeCTAR cluster:
         
  ```bash
    sudo cp planners/ff /usr/local/bin/.
  ```    


In the **local machine** (e.g., your laptop) that will dispatch game jobs to the cluster via the ` pacman_contest_cluster.py` script:

* unzip & zip (to pack and unpack submissions and files for transfer): `sudo apt-get install -y unzip zip`
* Python >= 3.5 with:
   * setuptools
   * iso8601
   * pytz
   * paramiko
* Simply run: `pip3 install -r requirements.txt --user`


In addition to that:

* Each submission is a `.zip` file or a directory; they should all go in a directory (e.g., `teams/`)
    * The player agent should be in the _root_ of the team zip file or team directory.
    * The name convention of a submission file/dir will depend on `--team-names-file` option.
    
* If option `--team-names-file` is passed, then submission file/dir names will be treated as student number and will be mapped to an actual team name using the mapping `.csv` file provided. Otherwise, submission file/dir name will be used as the team name. 
    * zip/dir should start with "`s`", continue with student number, then `_`, and then date in [iso8601 format](https://en.wikipedia.org/wiki/ISO_8601), then `.zip`
    * Format stored regexp `SUBMISSION_FILENAME_PATTERN`: `r'^(s\d+)_(.+)?\.zip$'`
    * Examples of legal team zip files:
        - `s2736172_2017-05-13T21:32:43.342000+10:00`
        - `s2736172_2017-05-13.zip`
    * Examples of team directories:
        - `Destructor_Pacman-05-13T21:32:43.342000+10:00`
        - `WeWillWin-05-13`
    * The student number will be mapped to a team and the timestamp will be used to pick the latest team submission.

* The cluster to be used is specified with option `--workers-file-path`, to point to a `.json` file containing the workers available (including no of cores, IP, username, password, and private key file if needed)


Hence, the user of this system must provide:

- *private keys* for cluster (if needed; specified in `workers.json`).
- Directory with set of zip submission files; see above (for option `--teams`)
- `workers.json`: listing the cluster setting to be used (for option `--workers-file-path`)
- `TEAMS-STUDENT-MAPPING.csv` [optional]: a CSV mapping student ids to team names (for option `--team-names-file`)
    - Main columns are: `STUDENT_ID` and `TEAM_NAME`
    - If no file provided is provided, team names are taken directly from the submitted zip files (this is the option used at unimelb).


## MAIN COMPONENTS 

The main script ` pacman_contest_cluster.py` runs a full contest and uses:

- `cluster_manager.py`: the support script to manage clusters (used by ` pacman_contest_cluster.py`).
- `contest.zip`: the actual main contest infrastructure, based on that one from UC (with minor fixes, e.g., delay in replays, upgraded to Python 3.x)
- `layouts.zip`: some interesting layouts that can be used (beyond the randomly generated ones)
- `staff_team_{basic,medium,top}.zip`: the teams from staff, used for `--include-staff-team` option. 
    - You can point to the directory containing all three staff agents using `--staff-teams-dir` (default is current dir)
	- You can use your own basic, medium, top agents, as long as they are named accordingly.  
	- If you want to use our agents, co ntact us. These teams are not shared as they are used for marking purposes. So, if
	    you get access to them, please do not distribute.
- `TEAMS-STUDENT-MAPPING.csv`: example of a mapping file

In addition:

- `driver.py`: downloads teams from submissions server, runs ` pacman_contest_cluster.py` and upload results into the web.
- `contest/` subdir: developing place for `contest.zip`. 


## OVERVIEW OF MARKING PROCESS

In a nutshell, the script follows the following steps:

1. Authenticates to all workers specified.
2. Collect all the teams. 
    - If option `--ignore-file-name-format` is given, then it will simply collect the team names from the `<teamname>.zip` files.
    - Otherwise, it will assume a file name `s<student number>_<timestamp>.zip`. The student number will be mapped to the team name (via the provided mapping in `--team-names-file`) and the last submission (using the timetsamps) will be selected.
3. Take `contest.zip`, `layouts.zip` (where some fixed layouts are stored), and the set of collected set of teams and:
    1. create a temporary full contest dir `contest-tmp`;
    2. zip it into `contest_and_teams.zip` file;
    3. transfer  `contest_and_teams.zip` to each available worker.
3. For each game:
    1. expand in `contest_and_teams.zip` to `/tmp/cluster_xxxxxxx`;
    2. run game;
    3. copy back log and replay to marking machine. 
4. Produce stat files as JSON files (can be used to generate HTML pages).


The full contest is **all-against-all tournament** with the following rank generation:
 
 * 3 points per win; 1 point per tie; 0 points per lose. Failed games are loses. 
 * Ordered by: points first, no. of wins second, score points third.
   


## EXAMPLE RUNS

### Run a contest
Using a CSV file to specify team names, include staff teams:

````bash
$ python3  pacman_contest_cluster.py --compress-log \
        --organizer "RMIT COSC1125/1127 - Intro to AI" \
        --teams-root AI17-contest/teams/  \
        --team-names-file AI17-contest/AI17-Contest-TEAMS.csv  \
        --www-dir www/ \
        --max-steps 1200 \
        --no-fixed-layouts 5 --no-random-layouts 10 \
        --workers-file AI1-contest/workers/nectar-workers.jason  
        --staff-teams-dir AI17-contest/staff-teams/
````

Collecting submitted files in teams, and using the zip filename as teamname, and uploading the replays file only into a sharing file service instead of your local directory:

````bash
$ python3  pacman_contest_cluster.py --compress-log \
        --organizer "UoM COMP90054/2018 - AI Planning" \
        --teams-root AI17-contest/teams/  \
        --www-dir www/ \
        --max-steps 1200 \
        --no-fixed-layouts 5 --no-random-layouts 10 \
        --workers-file AI1-contest/workers/nectar-workers.jason  
        --staff-teams-dir AI17-contest/staff-teams/
        --upload-www-replays
````
### Run contest only vs staff teams

Append this option to the command above ``` --staff-teams-vs-others-only```


### Resume partial contest

It is possible to **resume** an existing failed/partial competition or **repeat** a specific competition by using the option `--resume-contest-folder`.

So, if a run fails and is incomplete, all the logs generated so far can be found in the folder ``tmp\logs-run`` in your the local machine cloned repo.

To _resume_ the competition (so that all games played are used and not re-played):

1. Copy the temporal files into a different temporal folder: `mv tmp tmp-failed`. This is important, the folder `tmp/` as is cannot be used as it will be re-generated for each contest.
2. Tell the script to use that folder to get the existing logs by appending `--resume-contest-folder tmp-failed/`
3. Tell the script which are all the layouts to be used (those that were originally used in the failed run):
    * Use  `--fixed-layout-seeds` followed by the names of all fixed layouts that are to be used, separated by commas. 
        * E.g., `--fixed-layout-seeds contest05Capture,contest16Capture,contest20Capture`
    * Use `--random-seeds` followed by the seed numbers of all random layouts that are to be used, separated by commas.
        * E.g., `--random-seeds 7669,1332`

The `--fixed-layout-seeds` and `--random-seeds` options are also useful if you want to force the script to use some specific layouts. Look in folder [layouts/](layouts/) for available fixed, non-random, layouts.


Note that if the seeds given are less than the number of layouts asked for, the remaining are completed randomly.

The seeds for the fixed and random layouts used at each tournament are printed at the start, so one can recover them. 
However, if you need to recover the layouts played in the `tmp/` subdirectory, you can get them as follows:

1. For the random seeds: 

    ```bash
    $ ls -la tmp/logs-run/ |  grep RANDOM | sed -e "s/.*RANDOM\(.*\)\.log/\1\,/g" | sort -u | xargs -n 100
    ```

2. For the fixed layouts: 

    ```bash
    $ ls -la tmp/logs-run/ |  grep -v RANDOM | grep log | sed -e "s/.*_\(.*\)\.log/\1\,/g" | sort -u | xargs -n 100
    ```


### Re-run only some teams in a given contest

If only one or a few teams failed, one can just re-run those ones by basically deleting their logs from the temporary folder:

1. Load the new code of the team.
2. Remove all the logs from the temporal folder.
3. Re-run the competition using the same method commented above. 

That will only run the games for the logs you deleted.

### Re-run only updated teams

One quick and good strategy is to run a big contest but re-playing all games where one of the teams was updated.

To do so, we use the above method but we first delete all the logs of the teams that have been updated:

```bash
for d in `cat ai20-contest-timestamps.csv | grep updated | awk -F "\"*,\"*" '{print $1}'` ; do find tmp-failed/contest-a/logs-run/ -name \*$d* ; done
```

This takes advantage of the cloning script that leaves a column in the csv file stating whether the repo was updated or not from the last cloning.


## WEB PAGE GENERATION

A contest will leave JSON files with all stats, replays, and logs, from which a web page can be produced.

For example, to build web page in `www/` from stats, replays, and logs dirs:

````bash
$ python3 pacman_html_generator.py --organizer "Inter Uni RMIT-Mel Uni Contest" \
    --www-dir www/ \
    --stats-archive-dir stats-archive/  \
    --replays-archive-dir replays-archive/ \ 
    --logs-archive-dir logs-archive/
````

or if all stats, replays, and logs are within `www/` then just:

````bash
$ python3 pacman_html_generator.py --organizer "Inter Uni RMIT-Mel Uni Contest" --www-dir www/
````

**Observation:** If the stats file for a run has the `transfer.sh` URL for logs/replays, those will be used.


## SCHEDULE COMPETITION


If you want to automate the tournament, use the `driver.py` provided. It has the following options:

```bash
  --username [USERNAME]
                        username for --teams-server-url or for https git connection
  --password [PASSWORD]
                        password for --teams-server-url or for https git connection
  --dest-www [DEST_WWW]
                        Destination folder to publish www data in a web
                        server. (it is recommended to map a web-server folder
                        using smb)
  --teams-server-folder [TEAMS_SERVER_FOLDER]
                        folder containing all the teams submitted at the
                        server specified at --teams-server-name
  --teams-server-url [TEAMS_SERVER_URL]
                        server address containing the teams submitted
  --teams-git-csv [TEAMS_GIT_CSV] 
                        CSV containining columns TEAM, 'GitLab SSH repository link' and 'GitLab https repository link' 
  --tournament-cmd [TOURNAMENT_CMD]
                        specify all the options to run pacman-ssh-contesy.py
  --cron-script-folder [CRON_SCRIPT_FOLDER]
                        specify the folder to the scripts in order to run cron
```

You can run a competition using the following command:

```bash
$ driver.py --dest-www '' --teams-git-csv xxx --tournament-cmd '--compress-log --organizer "UoM COMP90054/2018 - AI Planning" ...'
```

It uses a csv file with the links to github/bitbucket/gitlab or any git server containing the code of each team, and downloads the submissions that have the *tag submission-contest* (see [driver.py](driver.py#lines-37)).


### Test command to schedule 

We strongly recommend to test the command you want to schedule in **cron**

Run the following command:
```
crontab -e
```

and introduce the following line into **cronfile** (change *username* appropriately)

```
# For more information see the manual pages of crontab(5) and cron(8)
# 
# m h  dom mon dow   command

* * * * *  /usr/bin/env > /home/username/cron-env
```

Now you can test the command you want to schedule by running
```
./run-as-cron /home/username/cron-env "<command>"
```

This will run you command with the same environment settings as cron jobs do. If the command succeeds, then you can set up your command now.

### Setting up cron 

Run the following command:

```bash
crontab -e
```

Remove the line you introduced before and introduce the following line:

```bash
# For more information see the manual pages of crontab(5) and cron(8)
# 
# m h  dom mon dow   command

01 00 * * * python driver.py --username xxx --password xxx --cron-script-folder ''  --dest-www '' --teams-server-folder '' --teams-server-url xxx --tournament-cmd ''
```

Now your script will run every midnight at 00:01

## MODIFYING THE CONTEST GAME

The code implementing a game simulator between two players is located in `contest/` as a _git submodule_ from [pacman-contest-agent](https://github.com/AI4EDUC/pacman-contest-agent) repository, which also serves as an empty agent template.

As of 2019, that code runs under Python 3.x. The game simulator for Python 2.7 is kept in repository [pacman-contest-27](https://github.com/AI4EDUC/pacman-contest-27/) repository. 

Note that the submodule source under `contest/` is NOT used for the actual cluster tournament, which only uses the source packed in `contest.zip` file. 

It is however left there under `contest/` just in case one wants to run and test specific single games, if needed. For example, if we assume that `contest/teams` points to a set of teams, we can run one game as follows:

```bash
$ cd contest/
$ python3 capture.py -r teams/staff_team_super/myTeam.py -b teams/staff_team_medium/myTeam.py
```

Remember that to get the source from its repo, one needs to do this before:

```bash
$ git submodule init
$ git submodule update --remote
```

Since the actual simulator code used by the cluster contest script is the one packed in `contest.zip`, any changes, fixes, upgrades, extensions to the simulator have to be done outside and zipped it into `contest.zip` file again.

For example, if one modifies the code in `contest/`, a new `contest.zip` can be generated as follows:

```bash
$ rm -f contest.zip ; cd contest/ ; zip -r  ../contest.zip * ; cd ..
```





## TROUBLESHOOTING 

* Cannot connect all hosts with message: _"Exception: Error reading SSH protocol banner"_
    * This happens when a single host has more than 10 CPUs.
    * The problem is not the script, but the ssh server in the cluster. By default it does not accept more than 10 connections. 
    * Configure `/etc/ssh/sshd_config:` in the host with `MaxStartups 20:30:60`
    * Check [this issue](https://github.com/ssardina-teaching/pacman-contest/issues/26)




## SCREENSHOT

![Contest Result](extras/screenshot01.png)



## LICENSE

This project is using the GPLv3 for open source licensing for information and the license visit GNU website (https://www.gnu.org/licenses/gpl-3.0.en.html).

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.
