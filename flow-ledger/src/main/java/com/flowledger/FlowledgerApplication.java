package com.flowledger;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class FlowledgerApplication {
  public static void main(String[] args) {
    SpringApplication.run(FlowledgerApplication.class, args);
  }
}
