#!/usr/bin/python3

import os
import sys

src_dir = os.path.join('..', '..', 'src')
sys.path.insert(0, src_dir)

from Resources.foundation.cli.command.CommandFactory import CommandFactory

if __name__ == '__main__':
    COMMAND_DIR = os.path.join(src_dir, 'Resources', 'cli', 'command')

    FILE_TEMPLATE = '''
    _remove_used_args()
    {
        local -n _COMP_WORDS=$1
        local -n _args=$2
        local result=$_args
        
        for ((i=2; i<${#_COMP_WORDS[@]}; i++)); do 
            opt=${_COMP_WORDS[$i]}
            result=$(echo "$result" | tr -d "\\n" | ''' \
                    '''awk -v opt="$opt" 'BEGIN {RS=" "}; {replaced=gsub("^"opt"$", ""); ''' \
                    '''if(replaced == 0){ print $0" "; }}')
        done
        
        echo "$result"
    }
    
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
    complete -F _kathara kathara'''

    if_template = '''
        if [[ ${prev} == %s || ${command} == %s ]]; then
            COMPREPLY=( $(compgen -W  "%s" -- ${cur}) )
            return 0
    '''

    elif_template = '''
        elif [[ ${prev} == %s || ${command} == %s ]]; then
            command_args="%s"
            filtered_args="$(_remove_used_args COMP_WORDS command_args)"
            COMPREPLY=( $(compgen -W  "${filtered_args}" -- ${cur}) )
            return 0
    '''

    if len(sys.argv) > 2:
        exit(1)

    path = '.' if len(sys.argv) < 2 else sys.argv[1]

    commands_table = {}
    for command_class in os.listdir(COMMAND_DIR):
        if 'Command' not in command_class:
            continue

        command_name = command_class.replace('Command.py', '')
        command_object = CommandFactory().create_instance(class_args=(command_name,))

        if hasattr(command_object, 'parser'):
            actions = []
            for action in command_object.parser._actions:
                actions.extend(action.option_strings)
            commands_table[command_name.lower()] = actions
        else:
            commands_table[command_name.lower()] = ""

    opts = ' '.join(commands_table.keys())

    commands_options = ''
    for command_name, command_opts in commands_table.items():
        command_opts_string = ' '.join(command_opts)
        commands_options += elif_template % (command_name, command_name, command_opts_string)

    autocompletion_file_str = FILE_TEMPLATE % (opts, commands_options)
    with open(os.path.join(path, 'kathara_autocompletion'), 'w') as bash_completion_file:
        bash_completion_file.write(autocompletion_file_str)
