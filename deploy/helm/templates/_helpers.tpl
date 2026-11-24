{{- define "camply.fullname" -}}
{{- default (printf "%s-%s" .Release.Name (default .Chart.Name .Values.nameOverride)) .Values.fullnameOverride | trunc 47 | trimSuffix "-" -}}
{{- end -}}

{{- define "camply.labels" -}}
app.kubernetes.io/name: {{ default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | quote }}
{{- end -}}

{{- define "camply.selector" -}}
app.kubernetes.io/name: {{ default .root.Chart.Name .root.Values.nameOverride | trunc 63 | trimSuffix "-" | quote }}
app.kubernetes.io/instance: {{ .root.Release.Name | quote }}
app.kubernetes.io/component: {{ .role | quote }}
{{- end -}}

{{- define "camply.image" -}}
{{- if .Values.image.digest -}}
{{ .Values.image.repository }}@{{ .Values.image.digest }}
{{- else -}}
{{ .Values.image.repository }}:{{ default .Chart.AppVersion .Values.image.tag }}
{{- end -}}
{{- end -}}

{{- define "camply.migrationName" -}}
{{- $identity := printf "%s-%s-%s" (toJson .Values) .Chart.Version (toString .Release.Revision) -}}
{{ include "camply.fullname" . | trunc 36 | trimSuffix "-" }}-migrate-{{ $identity | sha256sum | trunc 12 }}
{{- end -}}

{{- define "camply.databaseHost" -}}
{{- if .Values.postgresql.enabled -}}
{{ include "camply.fullname" . }}-postgresql
{{- else -}}
{{ required "database.host is required with external PostgreSQL" .Values.database.host }}
{{- end -}}
{{- end -}}

{{- define "camply.env" -}}
{{- $root := .root -}}
{{- $env := mergeOverwrite (deepCopy $root.Values.env) (deepCopy .config.env) -}}
{{- if eq .role "frontend" -}}
{{- $_ := set $env "CAMPLY_BACKEND_URL" (printf "http://%s-backend:%v" (include "camply.fullname" $root) $root.Values.backend.service.port) -}}
{{- else -}}
{{- $_ := set $env "CAMPLY_RUNTIME_MODE" "distributed" -}}
{{- $_ := set $env "SKIP_MIGRATIONS" "1" -}}
{{- $_ := set $env "CAMPLY_DB_DRIVERNAME" "postgresql+psycopg" -}}
{{- $_ := set $env "CAMPLY_DB_HOST" (include "camply.databaseHost" $root) -}}
{{- $_ := set $env "CAMPLY_DB_PORT" $root.Values.database.port -}}
{{- $_ := set $env "CAMPLY_DB_USERNAME" $root.Values.database.username -}}
{{- $_ := set $env "CAMPLY_DB_DATABASE" $root.Values.database.name -}}
{{- $_ := set $env "CAMPLY_DB_PASSWORD" (dict "valueFrom" (dict "secretKeyRef" (dict "name" $root.Values.database.existingSecret "key" $root.Values.database.passwordKey))) -}}
{{- if $root.Values.valkey.existingSecret -}}
{{- $_ := set $env "CAMPLY_VALKEY_URL" (dict "valueFrom" (dict "secretKeyRef" (dict "name" $root.Values.valkey.existingSecret "key" $root.Values.valkey.urlKey))) -}}
{{- else if $root.Values.valkey.enabled -}}
{{- $_ := set $env "CAMPLY_VALKEY_URL" (printf "redis://%s-valkey:6379/0" (include "camply.fullname" $root)) -}}
{{- else -}}
{{- $_ := set $env "CAMPLY_VALKEY_URL" (required "valkey.url or valkey.existingSecret is required with external Valkey" $root.Values.valkey.url) -}}
{{- end -}}
{{- $prometheus := $root.Values.prometheus.externalUrl -}}
{{- if $root.Values.prometheus.enabled -}}
{{- $prometheus = printf "http://%s-prometheus:9090" (include "camply.fullname" $root) -}}
{{- end -}}
{{- $_ := set $env "CAMPLY_PROMETHEUS_URL" $prometheus -}}
{{- $_ := set $env "PROMETHEUS_MULTIPROC_DIR" "/tmp/prometheus_multiproc" -}}
{{- $_ := set $env "CAMPLY_PROMETHEUS_MULTIPROC_DIR" "/tmp/prometheus_multiproc" -}}
{{- if eq .role "backend" -}}
{{- $_ := set $env "GUNICORN_PORT" "8000" -}}
{{- else -}}
{{- $_ := set $env "CAMPLY_METRICS_PORT" "8001" -}}
{{- end -}}
{{- if eq .role "beat" -}}
{{- $_ := set $env "CAMPLY_BEAT_HEALTH_FILE" "/tmp/camply-beat-health.json" -}}
{{- end -}}
{{- end -}}
{{- range $name, $value := $env }}
- name: {{ $name }}
  {{- if kindIs "map" $value }}
  {{- toYaml $value | nindent 2 }}
  {{- else }}
  value: {{ $value | toString | quote }}
  {{- end }}
{{- end -}}
{{- end -}}

{{- define "camply.scheduling" -}}
{{- with .Values.imagePullSecrets }}
imagePullSecrets: {{ toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.nodeSelector }}
nodeSelector: {{ toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.affinity }}
affinity: {{ toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.tolerations }}
tolerations: {{ toYaml . | nindent 2 }}
{{- end }}
{{- end -}}

{{- define "camply.storage" -}}
{{- if .enabled }}
persistentVolumeClaim:
  claimName: {{ default .name .existingClaim }}
{{- else }}
emptyDir: {}
{{- end }}
{{- end -}}

{{- define "camply.probe" -}}
{{- if not (and (kindIs "bool" .override) (not .override)) -}}
{{- $probe := deepCopy .default -}}
{{- if kindIs "map" .override -}}
{{- range $handler := list "httpGet" "exec" "tcpSocket" "grpc" -}}
{{- if hasKey $.override $handler -}}
{{- $_ := unset $probe "httpGet" -}}
{{- $_ := unset $probe "exec" -}}
{{- $_ := unset $probe "tcpSocket" -}}
{{- $_ := unset $probe "grpc" -}}
{{- end -}}
{{- end -}}
{{- $probe = mergeOverwrite $probe .override -}}
{{- end }}
{{ .name }}: {{ toYaml $probe | nindent 2 }}
{{- end -}}
{{- end -}}
