#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <termios.h>
#include <time.h>
#include <signal.h>

volatile int running = 1;

void signal_handler(int sig) {
    running = 0;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: %s <serial_port> <output_file>\n", argv[0]);
        printf("Example: %s /dev/cu.usbmodem157382101 data.txt\n", argv[0]);
        return 1;
    }
    
    const char *port = argv[1];
    const char *filename = argv[2];
    
    // Set up signal handler
    signal(SIGINT, signal_handler);
    
    // Open serial port
    int serial_fd = open(port, O_RDONLY | O_NOCTTY | O_NONBLOCK);
    if (serial_fd == -1) {
        perror("Failed to open serial port");
        return 1;
    }
    
    // Configure serial port for high speed
    struct termios tty;
    memset(&tty, 0, sizeof(tty));
    
    if (tcgetattr(serial_fd, &tty) != 0) {
        perror("tcgetattr failed");
        close(serial_fd);
        return 1;
    }
    
    // Set baud rate to 115200
    cfsetospeed(&tty, B115200);
    cfsetispeed(&tty, B115200);
    
    // 8N1 mode
    tty.c_cflag &= ~PARENB;
    tty.c_cflag &= ~CSTOPB;
    tty.c_cflag &= ~CSIZE;
    tty.c_cflag |= CS8;
    tty.c_cflag &= ~CRTSCTS;
    tty.c_cflag |= CREAD | CLOCAL;
    
    // Raw input
    tty.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);
    tty.c_iflag &= ~(IXON | IXOFF | IXANY);
    tty.c_oflag &= ~OPOST;
    
    if (tcsetattr(serial_fd, TCSANOW, &tty) != 0) {
        perror("tcsetattr failed");
        close(serial_fd);
        return 1;
    }
    
    // Open output file
    FILE *output_file = fopen(filename, "w");
    if (!output_file) {
        perror("Failed to open output file");
        close(serial_fd);
        return 1;
    }
    
    printf("Starting high-speed serial data collection...\n");
    printf("Port: %s\n", port);
    printf("Output: %s\n", filename);
    printf("Press Ctrl+C to stop\n\n");
    
    char buffer[1024];
    int total_lines = 0;
    time_t start_time = time(NULL);
    time_t last_log_time = start_time;
    
    while (running) {
        ssize_t bytes_read = read(serial_fd, buffer, sizeof(buffer) - 1);
        
        if (bytes_read > 0) {
            buffer[bytes_read] = '\0';
            
            // Write to file immediately
            fwrite(buffer, 1, bytes_read, output_file);
            fflush(output_file);
            
            // Count lines (JSON objects)
            char *line = strtok(buffer, "\n");
            while (line) {
                if (strlen(line) > 0 && line[0] == '{' && line[strlen(line)-1] == '}') {
                    total_lines++;
                    
                    // Log every 1000 lines
                    if (total_lines % 1000 == 0) {
                        time_t current_time = time(NULL);
                        double elapsed = difftime(current_time, start_time);
                        double rate = total_lines / elapsed;
                        printf("Collected %d data points (%.1f Hz)\n", total_lines, rate);
                        last_log_time = current_time;
                    }
                }
                line = strtok(NULL, "\n");
            }
        } else if (bytes_read == -1) {
            // No data available, tiny sleep
            usleep(100); // 0.1ms
        }
    }
    
    // Final stats
    time_t end_time = time(NULL);
    double total_duration = difftime(end_time, start_time);
    double final_rate = total_lines / total_duration;
    
    printf("\nData collection ended.\n");
    printf("Total: %d data points in %.1f seconds (%.1f Hz)\n", 
           total_lines, total_duration, final_rate);
    
    fclose(output_file);
    close(serial_fd);
    
    return 0;
} 