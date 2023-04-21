
#define left_touch_pin 22
#define right_touch_pin 23

String msg;
int msg_int;
int led_pin = 13;
int i=0; int j=0;
byte lick;
long left;
long right;
float curr_left = 0;
float curr_right = 0;
float threshold_multiplier_left = 1.1;
float threshold_multiplier_right = 1.1;
int total_bins = 2;
int counter_L = 0;
int counter_R = 0;

/*
 * LowPass Filter class is taken from https://github.com/curiores/ArduinoTutorials/blob/main/BasicFilters/ArduinoImplementations/LowPass/LowPass2.0/LowPass2.0.ino
 * and corresponding video tutorial is at: https://www.youtube.com/watch?v=eM4VHtettGg
 */
template <int order> // order is 1 or 2
class LowPass
{
  private:
    float a[order];
    float b[order+1];
    float omega0;
    float dt;
    bool adapt;
    float tn1 = 0;
    float x[order+1]; // Raw values
    float y[order+1]; // Filtered values

  public:  
    LowPass(float f0, float fs, bool adaptive){
      // f0: cutoff frequency (Hz)
      // fs: sample frequency (Hz)
      // adaptive: boolean flag, if set to 1, the code will automatically set
      // the sample frequency based on the time history.
      
      omega0 = 6.28318530718*f0;
      dt = 1.0/fs;
      adapt = adaptive;
      tn1 = -dt;
      for(int k = 0; k < order+1; k++){
        x[k] = 0;
        y[k] = 0;        
      }
      setCoef();
    }

    void setCoef(){
      if(adapt){
        float t = micros()/1.0e6;
        dt = t - tn1;
        tn1 = t;
      }
      
      float alpha = omega0*dt;
      if(order==1){
        a[0] = -(alpha - 2.0)/(alpha+2.0);
        b[0] = alpha/(alpha+2.0);
        b[1] = alpha/(alpha+2.0);        
      }
      if(order==2){
        float alphaSq = alpha*alpha;
        float beta[] = {1, sqrt(2), 1};
        float D = alphaSq*beta[0] + 2*alpha*beta[1] + 4*beta[2];
        b[0] = alphaSq/D;
        b[1] = 2*b[0];
        b[2] = b[0];
        a[0] = -(2*alphaSq*beta[0] - 8*beta[2])/D;
        a[1] = -(beta[0]*alphaSq - 2*beta[1]*alpha + 4*beta[2])/D;      
      }
    }

    float filt(float xn){
      // Provide me with the current raw value: x
      // I will give you the current filtered value: y
      if(adapt){
        setCoef(); // Update coefficients if necessary      
      }
      y[0] = 0;
      x[0] = xn;
      // Compute the filtered values
      for(int k = 0; k < order; k++){
        y[0] += a[k]*y[k+1] + b[k]*x[k];
      }
      y[0] += b[order]*x[order];

      // Save the historical values
      for(int k = order; k > 0; k--){
        y[k] = y[k-1];
        x[k] = x[k-1];
      }
  
      // Return the filtered value    
      return y[0];
    }
};

// Filter Instance
LowPass<1> lp_l(2, 1e4, true);
LowPass<1> lp_r(2, 1e4, true);


struct Base_Licks {
  float left;
  float right;
};
// Create a Base_Licks object
Base_Licks base_licks = {0.0, 0.0};

Base_Licks get_licks_baseline(Base_Licks base_licks) {
  float sum_left = 0;
  float sum_right = 0;
  int window_size = 1000;
  int led_pin = 13;
  digitalWrite(led_pin, HIGH);
  
  for (int i = 0; i < window_size; i++) {
    sum_left +=  lp_l.filt((touchRead(left_touch_pin)*5.0/1023.0 - 2.503)/0.185*1000);
    sum_right +=  lp_r.filt((touchRead(right_touch_pin)*5.0/1023.0 - 2.503)/0.185*1000);
  }  
  base_licks.left = sum_left / window_size;
  base_licks.right = sum_right / window_size;
  
  digitalWrite(led_pin, LOW);
  return base_licks;
}

Base_Licks get_licks(Base_Licks base_licks){   
  // Read and filter the lick sensor signals
  float curr_left = lp_l.filt((touchRead(left_touch_pin)*5.0/1023.0 - 2.503)/0.185*1000);
  float curr_right = lp_r.filt((touchRead(right_touch_pin)*5.0/1023.0 - 2.503)/0.185*1000);
  
  Serial.print(curr_left - threshold_multiplier_left*base_licks.left);
  Serial.print(',');
  Serial.println(curr_right - threshold_multiplier_right*base_licks.right);
  

  if (curr_left > threshold_multiplier_left*base_licks.left){
    counter_L = counter_L + 1;
    }
    
  if (curr_left < threshold_multiplier_left*base_licks.left){
    counter_L = 0;
    }
    
  if (curr_right > threshold_multiplier_right*base_licks.right){
    counter_R = counter_R + 1;
    }
    
  if (curr_right < threshold_multiplier_right*base_licks.right){
    counter_R = 0;
    }    

//  if (i==0 and (counter_L > total_bins)){
//      i = 1;   
//      lick=2;
//      Serial.println(lick);      // send 2 when left lick starts (-3 in python = -1)
//  }
//  if (i==1 and (counter_L < total_bins)){
//      i=0;
//      lick=1;
//      Serial.println(lick);   // send 1 when left lick ends (-3 in python = -2)
//  }
//      
//  if (j==0 and (counter_R > total_bins)){
//      j = 1;
//      lick=4;
//      Serial.println(lick);     // send 4 when right lick starts (-3 in python = 1)
//  }
//  if (j==1 and (counter_R < total_bins)){
//      j=0;
//      lick=5;
//      Serial.println(lick);   // send 5 when right lick ends (-3 in python = 2)  
//  } 

//  Serial.print(counter_L);
//  Serial.print(',');
//  Serial.println(counter_R);

  
}

void setup() {  
  Serial.begin(115200);
  Serial.setTimeout(5);
  base_licks = get_licks_baseline(base_licks);

  pinMode(led_pin, OUTPUT);
  
  // Reward arduino
  Serial1.begin(9600);
}

void loop() {
  // see if there's incoming serial data:
  if (Serial.available() > 0) {;
      
    // read and forward incoming string from serial buffer
    msg_int = int(Serial.parseInt());
    msg = Serial.readString();    
    Serial1.print(msg_int+msg);
    
    if (msg=="reset"){
      // Call the modified get_licks_baseline function and store the returned struct in my_licks
      base_licks = get_licks_baseline(base_licks);
    }

    // updating lick_threshold
    if (msg=="update_lick_threshold_left"){
        threshold_multiplier_left = msg_int; 
    }
    // updating lick_threshold
    if (msg=="update_lick_threshold_right"){
        threshold_multiplier_right = msg_int; 
    }
  }

//  get_licks(base_licks);


// Read and filter the lick sensor signals
  float curr_left = lp_l.filt((touchRead(left_touch_pin)*5.0/1023.0 - 2.503)/0.185*1000);
  float curr_right = lp_r.filt((touchRead(right_touch_pin)*5.0/1023.0 - 2.503)/0.185*1000);
  
//  Serial.print(curr_left - threshold_multiplier_left*base_licks.left);
//  Serial.print(',');
//  Serial.println(curr_right - threshold_multiplier_right*base_licks.right);

  if (curr_left > threshold_multiplier_left*base_licks.left){
    counter_L = counter_L + 1;
    }
    
  if (curr_left < threshold_multiplier_left*base_licks.left){
    counter_L = 0;
    }
    
  if (curr_right > threshold_multiplier_right*base_licks.right){
    counter_R = counter_R + 1;
    }
    
  if (curr_right < threshold_multiplier_right*base_licks.right){
    counter_R = 0;
    }    

  if (i==0 and (counter_L > total_bins)){
      i = 1;   
      lick=2;
      Serial.println(lick);      // send 2 when left lick starts (-3 in python = -1)
  }
  if (i==1 and (counter_L < total_bins)){
      i=0;
      lick=1;
      Serial.println(lick);   // send 1 when left lick ends (-3 in python = -2)
  }
      
  if (j==0 and (counter_R > total_bins)){
      j = 1;
      lick=4;
      Serial.println(lick);     // send 4 when right lick starts (-3 in python = 1)
  }
  if (j==1 and (counter_R < total_bins)){
      j=0;
      lick=5;
      Serial.println(lick);   // send 5 when right lick ends (-3 in python = 2)  
  } 

//  Serial.print(counter_L);
//  Serial.print(',');
//  Serial.println(counter_R);

}
