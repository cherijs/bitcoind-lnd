import logging
import subprocess

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s', )
logger = logging.getLogger(__name__)


def get_docker_ip(node):
    args = ['docker', 'inspect', '-f', "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", node]
    try:
        output = subprocess.check_output(args).decode().splitlines()
        return output[0]
    except subprocess.CalledProcessError as exc:
        if exc.returncode is 1:
            return False

        raise RuntimeError(
            "Command '{}' return with error (code {}): {}".format(
                exc.cmd, exc.returncode, exc.output))


def restart_docker(node):
    args = ['docker', 'restart', node]
    try:
        output = subprocess.check_output(args).decode().splitlines()
        logger.info(f'RESTARTED: {output[0]}')
        return output[0]
    except subprocess.CalledProcessError as exc:
        if exc.returncode is 1:
            return False

        raise RuntimeError(
            "Command '{}' return with error (code {}): {}".format(
                exc.cmd, exc.returncode, exc.output))
