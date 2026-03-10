data "aws_ami" "al2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_instance" "this" {
  ami                         = data.aws_ami.al2.id
  instance_type               = "t3.micro"
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [var.ec2_sg_id]
  iam_instance_profile        = var.instance_profile
  associate_public_ip_address = false
  user_data_replace_on_change = true

  user_data = <<-EOF
    #!/bin/bash
    set -u

    # Private subnet has no NAT. Do not install packages at boot.
    # Just make sure the preinstalled SSM agent is enabled/running.
    if systemctl list-unit-files | grep -q '^amazon-ssm-agent.service'; then
      systemctl enable --now amazon-ssm-agent || true
    fi
  EOF

}

output "instance_id" {
  value = aws_instance.this.id
}