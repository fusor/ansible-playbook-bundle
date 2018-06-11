# APB Tool Refactor


## Introduction
The apb tool's utility has grown from a few build commands to a large diverse
set of commands that interact with the broker, build containers, and help
developers build apbs.  The apb tool's code has grown significantly to account
for the new utility, but most of the growth was unilaterally in ```engine.py```.
Resulting in a lot of duplicate code and multiple code execution pathways that
are making bugs difficult to fix.

This leads me to propose to the community that I think the apb tool should
undergo some major changes. The focus would be to break apart ```engine.py```
into a series of classes in order to reuse code and unifiy duplicate code paths.

If the community is interested in changing the apb tool's structure then there
should be an addition consideration. Most of the future work for the apb tool
involves facilitating execution of an apb. This work, in python, is going to be
more difficult than if it were written in go because an apb tool written in go
can vendor the broker. This would reduce the amount of work to add the features,
isolate the code maintainace to the broker's code paths, and give the community
an addition way to test broker code.

Finally, my proposal to the community is to change the structure of the apb tool
in a two ways:
  - Break apart engine.py into a series of classes.
  - Re write the apb tool in Go.


## Class Structure
```bash
src/apb/
├── cli.go
├── commands
│   ├── apb_directory
│   │   ├── apb_directory.go
│   │   └── apb_init.go
│   ├── base.go
│   ├── broker_request
│   │   ├── broker_request.go
│   │   ├── apb_bootstrap.go
│   │   ├── apb_list.go
│   │   ├── apb_push.go
│   │   ├── apb_relist.go
│   │   ├── apb_remove.go
│   │   └── apb_run.go
│   ├── docker_command
│   │   ├── docker_command.go
│   │   ├── apb_build.go
│   │   └── apb_test.go
```


#### cli.go
The ```cli.go``` primary focus is command processing. It gathers and validates
input, then calls the corresponding subcommand with the appropriate arguments.
The subcommands will be classified into 3 groups:
  - Broker subcommands
  - Docker subcommands
  - Apb directory subcommands

```cli.go``` will expect a return value from the subcommand it called. Based on
that subcommand, the return value will be processed before its printed to
stdout. Some commands won't require any additional help printing something human
readable.


#### base.go
Base class for all commands


#### apb_<command>.go
Class for apb command logic


## Python to Golang discussion
Changing from Python to Go will benifit the apb execution future work. But,
there is also other avenues of work to consider, particularly that ansible
is written in python and we would be moving away from any python tools in that
area.  This is something that needs to be explored further before the rewrite
proceeds.


## Work Items
 - Investigate future work for the apb tool if it remains written in Python
 - Define a set of classes based on engine.py code
