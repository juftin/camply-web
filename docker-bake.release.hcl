variable "RELEASE_VERSION" {
  default = "latest"
}

target "backend" {
  tags = RELEASE_VERSION == "latest" ? ["ghcr.io/juftin/camply-backend:latest"] : [
    "ghcr.io/juftin/camply-backend:${RELEASE_VERSION}",
    "ghcr.io/juftin/camply-backend:v${split(".", RELEASE_VERSION)[0]}",
    "ghcr.io/juftin/camply-backend:latest",
  ]
}

target "frontend" {
  tags = RELEASE_VERSION == "latest" ? ["ghcr.io/juftin/camply-frontend:latest"] : [
    "ghcr.io/juftin/camply-frontend:${RELEASE_VERSION}",
    "ghcr.io/juftin/camply-frontend:v${split(".", RELEASE_VERSION)[0]}",
    "ghcr.io/juftin/camply-frontend:latest",
  ]
}
