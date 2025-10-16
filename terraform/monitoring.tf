# Cloud Monitoring Dashboards for epymodelingsuite
# These dashboards allow you to monitor CPU and memory usage for each stage

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
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" resource.type=\"gce_instance\" metadata.user_labels.stage=\"builder\""
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
                        filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metadata.user_labels.stage=\"builder\""
                        aggregation = {
                          alignmentPeriod  = "60s"
                          perSeriesAligner = "ALIGN_MEAN"
                        }
                      }
                      denominator = {
                        filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_size\" resource.type=\"gce_instance\" metadata.user_labels.stage=\"builder\""
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
                      filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metadata.user_labels.stage=\"builder\""
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
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/usage_time\" resource.type=\"gce_instance\" metadata.user_labels.stage=\"builder\""
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
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" resource.type=\"gce_instance\" metadata.user_labels.stage=\"runner\""
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
                        filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metadata.user_labels.stage=\"runner\""
                        aggregation = {
                          alignmentPeriod  = "60s"
                          perSeriesAligner = "ALIGN_MEAN"
                        }
                      }
                      denominator = {
                        filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_size\" resource.type=\"gce_instance\" metadata.user_labels.stage=\"runner\""
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
                      filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metadata.user_labels.stage=\"runner\""
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
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/usage_time\" resource.type=\"gce_instance\" metadata.user_labels.stage=\"runner\""
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
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" resource.type=\"gce_instance\" metadata.user_labels.stage=\"runner\""
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

# Dashboard 3: Overall System View - All stages combined
resource "google_monitoring_dashboard" "overall" {
  dashboard_json = jsonencode({
    displayName = "epymodelingsuite - Overall System"
    mosaicLayout = {
      columns = 48
      tiles = [
        # Overall CPU Utilization
        {
          width  = 24
          height = 16
          widget = {
            title = "Overall CPU Utilization (%) - All Stages"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" resource.type=\"gce_instance\" metadata.user_labels.component=\"epymodelingsuite\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_MEAN"
                        crossSeriesReducer = "REDUCE_MEAN"
                        groupByFields      = ["metadata.user_labels.stage"]
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
        # Overall Memory Usage (%)
        {
          xPos   = 24
          width  = 24
          height = 16
          widget = {
            title = "Overall Memory Usage (%) - All Stages"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilterRatio = {
                      numerator = {
                        filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metadata.user_labels.component=\"epymodelingsuite\""
                        aggregation = {
                          alignmentPeriod    = "60s"
                          perSeriesAligner   = "ALIGN_MEAN"
                          crossSeriesReducer = "REDUCE_SUM"
                          groupByFields      = ["metadata.user_labels.stage"]
                        }
                      }
                      denominator = {
                        filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_size\" resource.type=\"gce_instance\" metadata.user_labels.component=\"epymodelingsuite\""
                        aggregation = {
                          alignmentPeriod    = "60s"
                          perSeriesAligner   = "ALIGN_MEAN"
                          crossSeriesReducer = "REDUCE_SUM"
                          groupByFields      = ["metadata.user_labels.stage"]
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
        # CPU Core Usage (vCPU)
        {
          yPos   = 16
          width  = 24
          height = 16
          widget = {
            title = "Overall CPU Core Usage (vCPU) - All Stages"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/usage_time\" resource.type=\"gce_instance\" metadata.user_labels.component=\"epymodelingsuite\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_RATE"
                        crossSeriesReducer = "REDUCE_SUM"
                        groupByFields      = ["metadata.user_labels.stage"]
                      }
                    }
                  }
                  plotType   = "STACKED_AREA"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Memory Usage (MiB)
        {
          xPos   = 24
          yPos   = 16
          width  = 24
          height = 16
          widget = {
            title = "Overall Memory Usage (MiB) - All Stages"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\" resource.type=\"gce_instance\" metadata.user_labels.component=\"epymodelingsuite\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_MEAN"
                        crossSeriesReducer = "REDUCE_SUM"
                        groupByFields      = ["metadata.user_labels.stage"]
                      }
                    }
                  }
                  plotType   = "STACKED_AREA"
                  targetAxis = "Y1"
                }
              ]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },
        # Active Instances by Stage
        {
          yPos   = 32
          width  = 48
          height = 16
          widget = {
            title = "Active Instances by Stage"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\" resource.type=\"gce_instance\" metadata.user_labels.component=\"epymodelingsuite\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_MEAN"
                        crossSeriesReducer = "REDUCE_COUNT"
                        groupByFields      = ["metadata.user_labels.stage"]
                      }
                    }
                  }
                  plotType   = "STACKED_AREA"
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
