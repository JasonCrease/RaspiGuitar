/**
 * Command line interface to the custom baud rate for B38400.
 * Steve
 */

#include <errno.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/serial.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int set_custom_baud_rate(const char* deviceFilename, int speed)
{
  struct serial_struct ss;
  int port, closestSpeed, ret = 1;
  
  if(speed < 1)
    {
      errno = EINVAL;
      return 1;
    }

  port = open(deviceFilename, O_RDWR | O_NOCTTY | O_NONBLOCK);
  if(port != -1)
    {
      if(ioctl(port, TIOCGSERIAL, &ss) == 0)
	{
	  if(speed != 38400)
	    {
	      // configure port to use custom speed instead of 38400
	      ss.flags = (ss.flags & ~ASYNC_SPD_MASK) | ASYNC_SPD_CUST;
	      ss.custom_divisor = (ss.baud_base + (speed / 2)) / speed;
	      closestSpeed = ss.baud_base / ss.custom_divisor;
  
	      if (closestSpeed < speed * 98 / 100 || closestSpeed > speed * 102 / 100)
		{
		  errno = ENOTSUP;
		  fprintf(stderr, "Cannot set serial port speed to %d. Closest possible is %d\n", speed, closestSpeed);
		}
	      else
		{
		  printf("Closest speed is %d (baud_base=%d, custom_divisor=%d)\n", closestSpeed, ss.baud_base, ss.custom_divisor);
		  ret = 0;
		}
	    }
	  else
	    {
	      ss.flags &= ~ASYNC_SPD_MASK;
	      printf("Disabling custom baud rate\n");
	      ret = 0;
	    }
	  if(!ret)
	    {
	      ret = ioctl(port, TIOCSSERIAL, &ss);
	    }
	}
      close(port);
    }
  return ret;
}

int main(int argc, char *argv[])
{
  if(argc < 3)
    {
      fprintf(stderr, "Usage: %s device_filename baud_rate\n", argv[0]);
      return 1;
    }
  const char* deviceFilename = argv[1];
  int ret = 1;
  char *endptr = NULL;
  int speed = strtol(argv[2], &endptr, 10);
  if(*endptr) errno = EINVAL;
  if(!errno)
    {
      ret = set_custom_baud_rate(deviceFilename, speed);
    }
  if(ret)
    {
      perror("set_custom_baud_rate()");
    }
  return ret;
}
