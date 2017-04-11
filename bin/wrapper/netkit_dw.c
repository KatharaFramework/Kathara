#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_CMD_LEN 1000

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

void check_invalid_cp(char* p, int is_cp, int current_arg, int total_args) 
{
    if(is_cp==1 && current_arg < total_args-1 && strstr(p, ":") != NULL) 
    {
        fprintf(stderr, "cp from container to host is not allowed\n");
        exit(EXIT_FAILURE); 
    }
}

int main(int argc, char *argv[]) 
{

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
        int is_cp = 0;
        if(strncmp(argv[1], "cp", 2)==0) 
            is_cp = 1;
        int current_arg = 2;
        for(p = &argv[2]; *p; p++)
        {
            check_invalid_cp(*p, is_cp, current_arg, argc); 
            check_mount_option(*p);
            char_count += strlen(*p) + 1;
            check_overflow(char_count);
            strcat(cmd, " ");
            strcat(cmd, *p);
            current_arg++;
        }
        system(cmd);
    }

    return 0;
}
