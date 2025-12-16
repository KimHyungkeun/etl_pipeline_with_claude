package com.iot.pipeline.dto;

public class SensorReading {
    private String sensorId;
    private String sensorType;
    private String location;
    private Double value;
    private String unit;
    private String timestamp;

    public SensorReading() {}

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

    public String getTimestamp() { return timestamp; }
    public void setTimestamp(String timestamp) { this.timestamp = timestamp; }

    @Override
    public String toString() {
        return String.format("SensorReading{sensorId='%s', type='%s', value=%.2f, location='%s'}",
                sensorId, sensorType, value, location);
    }
}