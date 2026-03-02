# resource "aws_vpc" "main" {
#   cidr_block           = "10.0.0.0/16"
#   enable_dns_hostnames = true
#   enable_dns_support   = true

#   ##tags = merge(
#     var.common_##tags,
#     {
#       Name = "${var.name_suffix}-vpc"
#     }
#   )
# }

# resource "aws_internet_gateway" "main" {
#   vpc_id = aws_vpc.main.id

#   ##tags = merge(
#     var.common_##tags,
#     {
#       Name = "${var.name_suffix}-igw"
#     }
#   )
# }

# resource "aws_subnet" "public" {
#   count                   = 2
#   vpc_id                  = aws_vpc.main.id
#   cidr_block              = "10.0.${count.index + 1}.0/24"
#   availability_zone       = data.aws_availability_zones.available.names[count.index]
#   map_public_ip_on_launch = true

#   ##tags = merge(
#     var.common_##tags,
#     {
#       Name = "${var.name_suffix}-public-subnet-${count.index + 1}"
#     }
#   )
# }

# resource "aws_subnet" "private" {
#   count             = 2
#   vpc_id            = aws_vpc.main.id
#   cidr_block        = "10.0.${count.index + 10}.0/24"
#   availability_zone = data.aws_availability_zones.available.names[count.index]

#   ##tags = merge(
#     var.common_##tags,
#     {
#       Name = "${var.name_suffix}-private-subnet-${count.index + 1}"
#     }
#   )
# }

# resource "aws_route_table" "public" {
#   vpc_id = aws_vpc.main.id

#   route {
#     cidr_block = "0.0.0.0/0"
#     gateway_id = aws_internet_gateway.main.id
#   }

#   ##tags = merge(
#     var.common_##tags,
#     {
#       Name = "${var.name_suffix}-public-rt"
#     }
#   )
# }

# resource "aws_route_table_association" "public" {
#   count          = 2
#   subnet_id      = aws_subnet.public[count.index].id
#   route_table_id = aws_route_table.public.id
# }

# resource "aws_security_group" "rds" {
#   name        = "${var.name_suffix}-rds-sg"
#   description = "Security group for RDS PostgreSQL"
#   vpc_id      = aws_vpc.main.id

#   ingress {
#     from_port   = 5432
#     to_port     = 5432
#     protocol    = "tcp"
#      cidr_blocks = [var.allowed_ip_cidr]
#   }

#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }

#   ##tags = merge(
#     var.common_##tags,
#     {
#       Name = "${var.name_suffix}-rds-sg"
#     }
#   )
# }

# resource "aws_db_subnet_group" "main" {
#   name       = "${var.name_suffix}-db-subnet-group"
#   subnet_ids = concat(aws_subnet.public[*].id, aws_subnet.private[*].id)

#   ##tags = merge(
#     var.common_##tags,
#     {
#       Name = "${var.name_suffix}-db-subnet-group"
#     }
#   )
# }

# data "aws_availability_zones" "available" {
#   state = "available"
# }

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_region" "current" {}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  ##tags = merge(var.common_##tags, { Name = "${var.name_suffix}-vpc" })
}

# 2 subnets PRIVADAS (sem IGW, sem NAT)
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  ##tags = merge(var.common_##tags, { Name = "${var.name_suffix}-private-${count.index + 1}" })
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  ##tags   = merge(var.common_##tags, { Name = "${var.name_suffix}-private-rt" })
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# SG da EC2 (nenhum inbound; SSM não precisa)
resource "aws_security_group" "ec2" {
  name   = "${var.name_suffix}-ec2-ssm-sg"
  vpc_id = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # ##tags = merge(var.common_##tags, { Name = "${var.name_suffix}-ec2-ssm-sg" })
}

# SG do RDS: libera SOMENTE a EC2 (não IP do seu PC)
resource "aws_security_group" "rds" {
  name   = "${var.name_suffix}-rds-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    description     = "Postgres from EC2 (SSM)"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # ##tags = merge(var.common_##tags, { Name = "${var.name_suffix}-rds-sg" })
}

# DB subnet group só com subnets privadas (RDS privado)
resource "aws_db_subnet_group" "main" {
  name       = "${var.name_suffix}-db-subnet-private"
  subnet_ids = aws_subnet.private[*].id

  # ##tags = merge(var.common_##tags, { Name = "${var.name_suffix}-db-subnet-private" })
}

# --------- VPC Interface Endpoints (SSM) ----------
# Para a EC2 privada falar com SSM sem NAT/Internet:
# - ssm
# - ssmmessages
# - ec2messages
resource "aws_security_group" "vpce" {
  name   = "${var.name_suffix}-vpce-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    description     = "HTTPS from EC2 to VPC Endpoints"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # ##tags = merge(var.common_##tags, { Name = "${var.name_suffix}-vpce-sg" })
}

resource "aws_vpc_endpoint" "ssm" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ssm"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpce.id]
  private_dns_enabled = true

  # ##tags = merge(var.common_##tags, { Name = "${var.name_suffix}-vpce-ssm" })
}

resource "aws_vpc_endpoint" "ssmmessages" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ssmmessages"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpce.id]
  private_dns_enabled = true

  # ##tags = merge(var.common_##tags, { Name = "${var.name_suffix}-vpce-ssmmessages" })
}

resource "aws_vpc_endpoint" "ec2messages" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ec2messages"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpce.id]
  private_dns_enabled = true

  # ##tags = merge(var.common_##tags, { Name = "${var.name_suffix}-vpce-ec2messages" })
}

# --------- IAM role / instance profile para SSM ----------
resource "aws_iam_role" "ec2_ssm_role" {
  name = "${var.name_suffix}-ec2-ssm-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2_ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.name_suffix}-ec2-ssm-profile"
  role = aws_iam_role.ec2_ssm_role.name
}

# Outputs
output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "rds_security_group_id" {
  value = aws_security_group.rds.id
}

output "ec2_security_group_id" {
  value = aws_security_group.ec2.id
}

output "db_subnet_group_name" {
  value = aws_db_subnet_group.main.name
}

output "ec2_instance_profile_name" {
  value = aws_iam_instance_profile.ec2_profile.name
}