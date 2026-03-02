data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

resource "aws_instance" "this" {
  ami                         = data.aws_ami.al2023.id
  instance_type               = "t3.micro"
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [var.ec2_sg_id]
  iam_instance_profile        = var.instance_profile
  associate_public_ip_address = false

  #tags = merge(var.common_#tags, { Name = "${var.name_suffix}-bastion-ssm" })
}

output "instance_id" {
  value = aws_instance.this.id
}