def estimator(data):
  #Get the CurrentlyInfected for severe and impact cases
  currentInfectedImpact = CovidEstimator.currentlyInfectedImpact(data["reportedCases"])
  currentInfectedSevere = CovidEstimator.currentlyInfectedSevere(data["reportedCases"])
  # The infections by requested_time
  infectionsByRequestedTimeImpact = CovidEstimator.infectionsByTime(data["periodType"],data["timeToElapse"],currentInfectedImpact)
  infectionsByRequestedTimeSevere = CovidEstimator.infectionsByTime(data["periodType"],data["timeToElapse"],currentInfectedSevere)
  
  output_data = {
    "estimates": {
      "impact": {
            "currentlyInfected": currentInfectedImpact,
            "infectionsByRequestedTime":infectionsByRequestedTimeImpact 
            
        },
        "severe": {
            "currentlyInfected": currentInfectedSevere,
            "infectionsByRequestedTime":infectionsByRequestedTimeSevere 
            
        }
    }
  }
  return output_data




class CovidEstimator:
  def currentlyInfectedImpact(reportedCases):
    return reportedCases * 10
  def currentlyInfectedSevere(reportedCases):
    return reportedCases * 50
  def infectionsByTime(period_type,period,currently_infected):
    if period_type == "weeks":
      weeks_to_days = int(period) * 7
      factor = weeks_to_days // 3
      infections = currently_infected * (2 ** factor)
      return float(infections)

    elif period_type == "months":
      months_to_days = int(period) * 30
      factor = months_to_days // 3
      infections = currently_infected * (2**factor)
      return float(infections)
    
    else:
      factor = int(period) // 3
      infections = currently_infected * (2 ** factor)
      return float(infections)

