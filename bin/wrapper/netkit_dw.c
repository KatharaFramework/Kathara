#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>
#include <pwd.h>
#include <sys/types.h>

#define MAX_CMD_LEN 1500

char* allowed_words_1 [] = { "run", "exec", "kill", "rm", "stop", "start", "rmi", "connect", "create", "stats" };
char* allowed_words_2 [] = { "-ti", "-tid", "-it", "-itd", "-dit", "-dti", "--privileged=true", "--name", "--hostname=", "--network=", "--memory=", "-f", "-e", "-d"};
#define ALLOWED_WORDS_1_LEN 10
#define ALLOWED_WORDS_2_LEN 14

char* get_user_home() {
    struct passwd *passwdEnt = getpwuid(getuid());
    return passwdEnt->pw_dir;
}

void check_overflow(int count) 
{
    if (count >= MAX_CMD_LEN) 
    {
        fprintf(stderr, "The command is longer than the buffer\n");
        exit(EXIT_FAILURE);
    }
}

void check_mount_option(char* p) 
{
    if(strncmp("-v", p, 2)==0 || strncmp("--v", p, 3)==0) 
    {
        fprintf(stderr, "-v and volumes options are not allowed\n");
        exit(EXIT_FAILURE); 
    }
}

int is_run(char* p){
    return strncmp("run", p, 3)==0;
}

int is_path_in_container(char* p)
{
    return strstr(p, ":") != NULL;
}

int is_not_last_arg(int current_arg, int total_args)
{
    return current_arg < total_args-1;
}

int is_valid_cp(char* p, int current_arg, int total_args) 
{
    if(is_not_last_arg(current_arg, total_args) && is_path_in_container(p)) 
    {
        fprintf(stderr, "cp from container to host is not allowed\n");
        return 0;
    }
    return 1;
}

int contains(char* haystack[], char* needle, int len)
{
    
    for(int i = 0; i < len; ++i)
    {
        if(strncmp(haystack[i], needle, strlen(haystack[i]))==0) //ensures that words like --hostname=anything are accepted
        {
            return 1;
        }
    }
    return 0;
}

int is_allowed_word(char* p, char** allowed_words, int len, int strict)
{
    if(contains(allowed_words, p, len) || (strncmp("-", p, 1)!=0) && !strict)
        return 1;
    return 0;
}

int main(int argc, char *argv[]) 
{
    typedef enum {INITIAL, CP1, CP2, CPOK, NETWORK, OK} state;
    state current_state = INITIAL;

    char cmd[MAX_CMD_LEN] = "";
    char **p;

    if (argc < 2) /* no parameters */
    {
        fprintf(stderr, "Usage: netkit_dw [options] command\n");
        exit(EXIT_FAILURE);
    }
    else
    {
        strcat(cmd, "docker ");
        int char_count = 7 + strlen(argv[1]);
        check_overflow(char_count);
        strcat(cmd, argv[1]);
        if(is_run(argv[1])) {
             char* home_dir = get_user_home();
             char_count += strlen(home_dir) + 1 + 2 + 1 + 10 + 1;
             check_overflow(char_count);
             strcat(cmd, " -v ");
             strcat(cmd, home_dir);
             strcat(cmd, ":/hosthome ");
        }
        if(strncmp(argv[1], "cp", 2)==0) 
            current_state = CP1;
        else if(is_allowed_word(argv[1], allowed_words_1, ALLOWED_WORDS_1_LEN, 1))
            current_state = OK;
        else if(strncmp(argv[1], "network", 7)==0) 
            current_state = NETWORK;
        else 
        {   //current_stete = PIT;
            fprintf(stderr, "Usage: netkit_dw [options] command\n");
            exit(EXIT_FAILURE);
        }
        int current_arg = 2;
        for(p = &argv[2]; *p; p++)
        {
            if(current_state==CP1)
                if (is_valid_cp(*p, current_arg, argc))
                    current_state = CP2;
                else //current_stete = PIT;
                    exit(EXIT_FAILURE);
            if(current_state==CP2)
                if (is_valid_cp(*p, current_arg, argc))
                    current_state = CPOK; // there cannot be other arguments if we are here
                else //current_stete = PIT;
                    exit(EXIT_FAILURE);
            if(current_state==NETWORK)
                if (is_allowed_word(*p, allowed_words_1, ALLOWED_WORDS_1_LEN, 1))
                    current_state = OK;
                else 
                {   //current_stete = PIT;
                    fprintf(stderr, "Parameter %i not allowed (1)\n", current_arg);
                    exit(EXIT_FAILURE);
                }
            if(current_state==OK)
                if (is_allowed_word(*p, allowed_words_2, ALLOWED_WORDS_2_LEN, 0))
                    current_state = OK;
                else 
                {   //current_stete = PIT;
                    fprintf(stderr, "Parameter %i not allowed (2)\n", current_arg);
                    exit(EXIT_FAILURE);
                }
            check_mount_option(*p); // redundant check for -v parameter
            char_count += strlen(*p) + 1;
            check_overflow(char_count);
            strcat(cmd, " ");
            strcat(cmd, *p);
            current_arg++;
        }
        
        if(current_state==OK || current_state==CPOK)
        {
            setuid(0);
            system(cmd);
        }
    }

    return 0;
}
