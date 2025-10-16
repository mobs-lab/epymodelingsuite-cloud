# Cloud Monitoring Dashboards for epymodelingsuite
# These dashboards allow you to monitor CPU and memory usage for each stage

# Dashboard 1: Image Build (Cloud Build) - stage=imagebuild
resource "google_monitoring_dashboard" "imagebuild" {
  dashboard_json = jsonencode({
    displayName = "epymodelingsuite - Image Build (Cloud Build)"
    mosaicLayout = {
      columns = 48
      tiles = [
        # Cloud Build Execution Time
        {
          width  = 24
          height = 16
          widget = {
            title = "Cloud Build Execution Time"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"build\" AND resource.labels.build_trigger_id!=\"\""
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_DELTA"
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
        # Cloud Build Status
        {
          xPos   = 24
          width  = 24
          height = 16
          widget = {
            title = "Cloud Build Status (Success vs Failure)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"build\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_RATE"
                        crossSeriesReducer = "REDUCE_COUNT"
                        groupByFields      = ["metric.status"]
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

# Dashboard 2: Builder (Stage A - Dispatcher) - stage=builder
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
                      filter = "resource.type=\"gce_instance\" AND metadata.user_labels.stage=\"builder\" AND metric.type=\"compute.googleapis.com/instance/cpu/utilization\""
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
                        filter = "resource.type=\"gce_instance\" AND metadata.user_labels.stage=\"builder\" AND metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\""
                        aggregation = {
                          alignmentPeriod  = "60s"
                          perSeriesAligner = "ALIGN_MEAN"
                        }
                      }
                      denominator = {
                        filter = "resource.type=\"gce_instance\" AND metadata.user_labels.stage=\"builder\" AND metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_size\""
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
                      filter = "resource.type=\"gce_instance\" AND metadata.user_labels.stage=\"builder\" AND metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\""
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
                      filter = "resource.type=\"gce_instance\" AND metadata.user_labels.stage=\"builder\" AND metric.type=\"compute.googleapis.com/instance/cpu/usage_time\""
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
        # Batch Job Task Count for Builder
        {
          yPos   = 32
          width  = 48
          height = 16
          widget = {
            title = "Builder Batch Job Status"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"batch.googleapis.com/Job\" AND resource.labels.job_uid!=\"\" AND metadata.user_labels.stage=\"builder\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_MEAN"
                        crossSeriesReducer = "REDUCE_COUNT"
                        groupByFields      = ["resource.job_uid"]
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

# Dashboard 3: Runner (Stage B - Parallel Simulations) - stage=runner
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
                      filter = "resource.type=\"gce_instance\" AND metadata.user_labels.stage=\"runner\" AND metric.type=\"compute.googleapis.com/instance/cpu/utilization\""
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
                        filter = "resource.type=\"gce_instance\" AND metadata.user_labels.stage=\"runner\" AND metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\""
                        aggregation = {
                          alignmentPeriod  = "60s"
                          perSeriesAligner = "ALIGN_MEAN"
                        }
                      }
                      denominator = {
                        filter = "resource.type=\"gce_instance\" AND metadata.user_labels.stage=\"runner\" AND metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_size\""
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
                      filter = "resource.type=\"gce_instance\" AND metadata.user_labels.stage=\"runner\" AND metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\""
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
                      filter = "resource.type=\"gce_instance\" AND metadata.user_labels.stage=\"runner\" AND metric.type=\"compute.googleapis.com/instance/cpu/usage_time\""
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
        # Batch Job Task Count for Runner
        {
          yPos   = 32
          width  = 24
          height = 16
          widget = {
            title = "Runner Active Tasks"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"batch.googleapis.com/Job\" AND resource.labels.job_uid!=\"\" AND metadata.user_labels.stage=\"runner\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_MEAN"
                        crossSeriesReducer = "REDUCE_SUM"
                        groupByFields      = ["resource.job_uid"]
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
        # Parallelism view
        {
          xPos   = 24
          yPos   = 32
          width  = 24
          height = 16
          widget = {
            title = "Runner Parallelism (Concurrent Tasks)"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"gce_instance\" AND metadata.user_labels.stage=\"runner\""
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

# Dashboard 4: Overall System View - All stages combined
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
                      filter = "resource.type=\"gce_instance\" AND metadata.user_labels.component=\"epymodelingsuite\" AND metric.type=\"compute.googleapis.com/instance/cpu/utilization\""
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
                        filter = "resource.type=\"gce_instance\" AND metadata.user_labels.component=\"epymodelingsuite\" AND metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\""
                        aggregation = {
                          alignmentPeriod    = "60s"
                          perSeriesAligner   = "ALIGN_MEAN"
                          crossSeriesReducer = "REDUCE_SUM"
                          groupByFields      = ["metadata.user_labels.stage"]
                        }
                      }
                      denominator = {
                        filter = "resource.type=\"gce_instance\" AND metadata.user_labels.component=\"epymodelingsuite\" AND metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_size\""
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
                      filter = "resource.type=\"gce_instance\" AND metadata.user_labels.component=\"epymodelingsuite\" AND metric.type=\"compute.googleapis.com/instance/cpu/usage_time\""
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
                      filter = "resource.type=\"gce_instance\" AND metadata.user_labels.component=\"epymodelingsuite\" AND metric.type=\"compute.googleapis.com/instance/memory/balloon/ram_used\""
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
        # Active Batch Jobs by Stage
        {
          yPos   = 32
          width  = 48
          height = 16
          widget = {
            title = "Active Batch Jobs by Stage"
            xyChart = {
              chartOptions = {
                mode = "COLOR"
              }
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"batch.googleapis.com/Job\" AND metadata.user_labels.component=\"epymodelingsuite\""
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
