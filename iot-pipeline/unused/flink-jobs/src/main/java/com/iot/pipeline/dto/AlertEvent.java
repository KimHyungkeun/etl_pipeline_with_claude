package com.iot.pipeline.dto;

public class AlertEvent {
    private String alertId;
    private String sensorId;
    private String sensorType;
    private String location;
    private Double value;
    private String unit;
    private String alertType; // HIGH, LOW
    private Double threshold;
    private String timestamp;
    private String detectedAt;

    public AlertEvent() {}

    public String getAlertId() { return alertId; }
    public void setAlertId(String alertId) { this.alertId = alertId; }

    public String getSensorId() { return sensorId; }
    public void setSensorId(String sensorId) { this.sensorId = sensorId; }

    public String getSensorType() { return sensorType; }
    public void setSensorType(String sensorType) { this.sensorType = sensorType; }

    public String getLocation() { return location; }
    public void setLocation(String location) { this.location = location; }

    public Double getValue() { return value; }
    public void setValue(Double value) { this.value = value; }

    public String getUnit() { return unit; }
    public void setUnit(String unit) { this.unit = unit; }

    public String getAlertType() { return alertType; }
    public void setAlertType(String alertType) { this.alertType = alertType; }

    public Double getThreshold() { return threshold; }
    public void setThreshold(Double threshold) { this.threshold = threshold; }

    public String getTimestamp() { return timestamp; }
    public void setTimestamp(String timestamp) { this.timestamp = timestamp; }

    public String getDetectedAt() { return detectedAt; }
    public void setDetectedAt(String detectedAt) { this.detectedAt = detectedAt; }

    @Override
    public String toString() {
        return String.format("ALERT[%s] %s: %.2f %s (threshold: %.2f) at %s",
                alertType, sensorId, value, unit, threshold, location);
    }
}