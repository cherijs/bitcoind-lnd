import subprocess


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
