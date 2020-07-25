import os
import sys

sys.path.insert(0, '../../src')

from Resources.foundation.cli.command.CommandFactory import CommandFactory

command_dir = "../../src/Resources/cli/command"

FILE_TEMPLATE = '''
_kathara()
{
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="%s"
    command="${COMP_WORDS[1]}"
    sub=""
    
    if [[ ${prev} == -d ]] || [[ ${prev} == --directory ]] ; then
        _filedir -d      
        return 0
    %s
    elif [[ ${prev} == kathara ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur} ) )
        return 0
    fi
}
complete -F _kathara kathara
'''

if_template = '''
    if [[ ${prev} == %s || ${command} == %s ]]; then
        COMPREPLY=( $(compgen -W  "%s" -- ${cur}) )
        return 0
'''

elif_template = '''
    elif [[ ${prev} == %s || ${command} == %s ]]; then
        result="%s"
        len=${#COMP_WORDS[@]}
        for ((i=2; i<$len; i++)); do 
            opt=${COMP_WORDS[$i]}
            result=$(echo $result | awk -v opt="$opt"  'BEGIN { RS = " " } ; {a=gsub("^"opt"$", ""); if(a==0){ print }}')
        done
        COMPREPLY=( $(compgen -W  "${result}" -- ${cur}) )
        return 0
'''

commands_table = {}
for command_class in os.listdir(command_dir):
    if 'Command' not in command_class:
        continue
    command_name = command_class.replace('Command.py', '')
    command_object = CommandFactory().create_instance(class_args=(command_name,))
    if hasattr(command_object, 'parser'):
        actions = []
        for action in command_object.parser._actions:
            actions.extend(action.option_strings)
        commands_table[command_name.lower()] = actions

with open('/etc/bash_completion.d/kathara_autocompletion', 'w') as bash_completion_file:
    opts = ''
    for command in commands_table:
        opts += command + ' '

    command_options = ''

    for index, command in enumerate(commands_table):
        command_opts_string = ''
        for action in commands_table[command]:
            command_opts_string += action + ' '
        command_if = elif_template % (command, command, command_opts_string)
        command_options += command_if

    FILE_TEMPLATE = FILE_TEMPLATE % (opts, command_options)
    bash_completion_file.write(FILE_TEMPLATE)
