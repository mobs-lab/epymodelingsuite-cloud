# Cloud Monitoring Dashboards for epymodelingsuite
# These dashboards monitor CPU and memory usage for Cloud Batch jobs
# Note: Cloud Batch VMs are managed internally and don't expose user labels directly
# We use instance_name patterns and resource labels to filter metrics

# Dashboard 1: Builder (Stage A - Dispatcher) - stage=builder
resource "google_monitoring_dashboard" "builder" {
  dashboard_json = jsonencode({
    displayName = "epymodelingsuite - Builder (Stage A)"
    mosaicLayout = {
      columns = 48
      tiles = [
        # CPU Utilization for Builder
        {
          width  = 24
          height = 16
          widget = {
            title = "Builder CPU Utilization (%)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-a\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Memory Usage for Builder (%)
        {
          xPos   = 24
          width  = 24
          height = 16
          widget = {
            title = "Builder Memory Usage (%)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilterRatio = {
                      numerator = {
                        filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-a\")"
                        aggregation = {
                          alignmentPeriod  = "60s"
                          perSeriesAligner = "ALIGN_MEAN"
                        }
                      }
                      denominator = {
                        filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_size\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-a\")"
                        aggregation = {
                          alignmentPeriod  = "60s"
                          perSeriesAligner = "ALIGN_MEAN"
                        }
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Memory Usage for Builder (MiB)
        {
          yPos   = 16
          width  = 24
          height = 16
          widget = {
            title = "Builder Memory Usage (MiB)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-a\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # CPU Core Usage for Builder (vCPU)
        {
          xPos   = 24
          yPos   = 16
          width  = 24
          height = 16
          widget = {
            title = "Builder CPU Core Usage (vCPU)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/usage_time\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-a\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_RATE"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        }
      ]
    }
  })
}

# Dashboard 2: Runner (Stage B - Parallel Simulations) - stage=runner
resource "google_monitoring_dashboard" "runner" {
  dashboard_json = jsonencode({
    displayName = "epymodelingsuite - Runner (Stage B)"
    mosaicLayout = {
      columns = 48
      tiles = [
        # CPU Utilization for Runner
        {
          width  = 24
          height = 16
          widget = {
            title = "Runner CPU Utilization (%)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-b.*\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Memory Usage for Runner (%)
        {
          xPos   = 24
          width  = 24
          height = 16
          widget = {
            title = "Runner Memory Usage (%)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilterRatio = {
                      numerator = {
                        filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-b.*\")"
                        aggregation = {
                          alignmentPeriod  = "60s"
                          perSeriesAligner = "ALIGN_MEAN"
                        }
                      }
                      denominator = {
                        filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_size\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-b.*\")"
                        aggregation = {
                          alignmentPeriod  = "60s"
                          perSeriesAligner = "ALIGN_MEAN"
                        }
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Memory Usage for Runner (MiB)
        {
          yPos   = 16
          width  = 24
          height = 16
          widget = {
            title = "Runner Memory Usage (MiB)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-b.*\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # CPU Core Usage for Runner (vCPU)
        {
          xPos   = 24
          yPos   = 16
          width  = 24
          height = 16
          widget = {
            title = "Runner CPU Core Usage (vCPU)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/usage_time\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-b.*\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_RATE"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Parallelism view - count of active instances
        {
          yPos   = 32
          width  = 48
          height = 16
          widget = {
            title = "Runner Parallelism (Active Instances)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-b.*\")"
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_MEAN"
                        crossSeriesReducer = "REDUCE_COUNT"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        }
      ]
    }
  })
}

# Dashboard 3: Output (Stage C - Output Generation) - stage=output
resource "google_monitoring_dashboard" "output" {
  dashboard_json = jsonencode({
    displayName = "epymodelingsuite - Output (Stage C)"
    mosaicLayout = {
      columns = 48
      tiles = [
        # CPU Utilization for Output
        {
          width  = 24
          height = 16
          widget = {
            title = "Output CPU Utilization (%)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-c.*\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Memory Usage for Output (%)
        {
          xPos   = 24
          width  = 24
          height = 16
          widget = {
            title = "Output Memory Usage (%)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilterRatio = {
                      numerator = {
                        filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-c.*\")"
                        aggregation = {
                          alignmentPeriod  = "60s"
                          perSeriesAligner = "ALIGN_MEAN"
                        }
                      }
                      denominator = {
                        filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_size\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-c.*\")"
                        aggregation = {
                          alignmentPeriod  = "60s"
                          perSeriesAligner = "ALIGN_MEAN"
                        }
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Memory Usage for Output (MiB)
        {
          yPos   = 16
          width  = 24
          height = 16
          widget = {
            title = "Output Memory Usage (MiB)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-c.*\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # CPU Core Usage for Output (vCPU)
        {
          xPos   = 24
          yPos   = 16
          width  = 24
          height = 16
          widget = {
            title = "Output CPU Core Usage (vCPU)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/usage_time\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-c.*\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_RATE"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        }
      ]
    }
  })
}

# Dashboard 4: Overall System View - All stages combined
resource "google_monitoring_dashboard" "overall" {
  dashboard_json = jsonencode({
    displayName = "epymodelingsuite - Overall System"
    mosaicLayout = {
      columns = 48
      tiles = [
        # Overall CPU Utilization - Stage A
        {
          width  = 24
          height = 16
          widget = {
            title = "Stage A (Builder) - CPU Utilization (%)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-a\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Overall CPU Utilization - Stage B
        {
          xPos   = 24
          width  = 24
          height = 16
          widget = {
            title = "Stage B (Runner) - CPU Utilization (%)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-b.*\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Overall CPU Utilization - Stage C
        {
          width  = 24
          height = 16
          yPos   = 16
          widget = {
            title = "Stage C (Output) - CPU Utilization (%)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-c.*\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Overall Memory - Stage A
        {
          yPos   = 32
          width  = 24
          height = 16
          widget = {
            title = "Stage A (Builder) - Memory Usage (MiB)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-a\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Overall Memory - Stage B
        {
          xPos   = 24
          yPos   = 32
          width  = 24
          height = 16
          widget = {
            title = "Stage B (Runner) - Memory Usage (MiB)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-b.*\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Overall Memory - Stage C
        {
          xPos   = 24
          yPos   = 16
          width  = 24
          height = 16
          widget = {
            title = "Stage C (Output) - Memory Usage (MiB)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-c.*\")"
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Active Instances - All Stages
        {
          yPos   = 48
          width  = 48
          height = 16
          widget = {
            title = "Active Instances (All Stages)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" resource.type=\"gce_instance\" (metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-a\") OR metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-b.*\") OR metric.label.\"instance_name\"=monitoring.regex.full_match(\"epy-.*-stage-c.*\"))"
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_MEAN"
                        crossSeriesReducer = "REDUCE_COUNT"
                      }
                    }
                  }
                  plotType   = "LINE"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        }
      ]
    }
  })
}
