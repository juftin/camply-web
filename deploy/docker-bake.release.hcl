variable "RELEASE_VERSION" {
  default = "latest"
}

variable "GITHUB_SHA" {
  default = ""
}

target "backend" {
  tags = RELEASE_VERSION == "latest" ? ["ghcr.io/juftin/camply:latest"] : [
    "ghcr.io/juftin/camply:v${split(".", RELEASE_VERSION)[0]}",
    "ghcr.io/juftin/camply:v${RELEASE_VERSION}",
    "ghcr.io/juftin/camply:${substr(GITHUB_SHA, 0, 7)}",
    "ghcr.io/juftin/camply:latest",
  ]
}
