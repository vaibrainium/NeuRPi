
#define left_touch_pin 15
#define right_touch_pin 16 // 3

String msg;
int msg_int;
int led_pin = 13;
int start_millis;

int i=0; int j=0;
byte lick;
long left;
long right;
float curr_left = 0;
float curr_right = 0;
float prev_left = 0;
float prev_right = 0;

float threshold_multiplier_left = 1.2; //1.1;
float threshold_multiplier_right = 1.2; //1.1;
int left_threshold = 50;
int right_threshold = 50;
bool left_touched = false;
bool right_touched = false;

int total_bins = 2;
int counter_L = 0;
int counter_R = 0;
int slope = 5;
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
LowPass<1> lp_l(1, 1e6, true);
LowPass<1> lp_r(1, 1e6, true);


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
    delay(1);
    sum_right +=  lp_r.filt((touchRead(right_touch_pin)*5.0/1023.0 - 2.503)/0.185*1000);
  }
  base_licks.left = sum_left / window_size;
  base_licks.right = sum_right / window_size;

  digitalWrite(led_pin, LOW);
  return base_licks;
}

Base_Licks get_licks(Base_Licks base_licks, int start_millis, int left_threshold, int right_threshold){

//  Serial.print(touchRead(left_touch_pin));
//  Serial.print(',');
//  Serial.println(touchRead(right_touch_pin));
//  delay(1);

//  Serial.print(lp_l.filt((touchRead(left_touch_pin)*5.0/1023.0 - 2.503)/0.185*1000));
//  Serial.print(',');
//  Serial.println(lp_r.filt((touchRead(right_touch_pin)*5.0/1023.0 - 2.503)/0.185*1000));
//  delay(1);

//  // Read and filter the lick sensor signals
////  delay(1);
//  float curr_left = lp_l.filt((touchRead(left_touch_pin)*5.0/1023.0 - 2.503)/0.185*1000);
//  curr_left = map(curr_left, 0, 1000000, 0, 1000);
////  curr_left = map(curr_left - threshold_multiplier_left*base_licks.left, 0, 1000000, 0, 1000);
////  delay(1);
//  float curr_right = lp_r.filt((touchRead(right_touch_pin)*5.0/1023.0 - 2.503)/0.185*1000);
//  curr_right = map(curr_right, 0, 1000000, 0, 1000);
////  curr_right = map(curr_right - threshold_multiplier_right*base_licks.right, 0, 1000000, 0, 1000);
////  Serial.print(curr_left);
////  Serial.print(",");
////  Serial.println(curr_right);
//
//
  slope = 0;
  if (curr_left-prev_left > slope){
    counter_L = counter_L + 1;
    }

  if (curr_left-prev_left < -(.1*slope)){
    counter_L = 0;
    }

  if (curr_right-prev_right > slope){
    counter_R = counter_R + 1;
    }

  if (curr_right-prev_right < -(.1*slope)){
    counter_R = 0;
    }


  Serial.print(counter_L);
  Serial.print(",");
  Serial.println(counter_R);

//
//    if ((counter_L > 3) && !(left_touched)){
//    left_touched = true;
//    Serial.print(millis() - start_millis);
//    Serial.print("/t");
//    Serial.println(-1);
//    digitalWrite(led_pin, HIGH);
//    delay(50);
//    }
//
//   else if ((counter_L < 3) && (left_touched)){
//    left_touched = false;
//    Serial.print(millis() - start_millis);
//    Serial.print("/t");
//    Serial.println(-2);
//    digitalWrite(led_pin, LOW);
//    }
//
//  else if ((counter_R > 3) && !(right_touched)){
//    right_touched = true;
//    Serial.print(millis() - start_millis);
//    Serial.print("/t");
//    Serial.println(1);
//    digitalWrite(led_pin, HIGH);
//    delay(50);
//    }
//
//   else if ((counter_R < 3) && (right_touched)){
//    right_touched = false;
//    Serial.print(millis() - start_millis);
//    Serial.print("/t");
//    Serial.println(2);
//    digitalWrite(led_pin, LOW);
//    }
//
  prev_left = curr_left;
  prev_right = curr_right;
//
////    Serial.print(counter_L);
////    Serial.print(',');
////    Serial.println(counter_R);
//
////  curr_left = constrain(curr_left, 0, 255);
////  curr_right = constrain(curr_right, 0, 255);
////  Serial.print(curr_right);
////  Serial.print(",");
////  Serial.println(curr_left);

//
////  Serial.print(left_threshold);
////  Serial.print(",");
////  Serial.println(right_threshold);
//
////  if ((curr_left > left_threshold) && !(left_touched)){
////    left_touched = true;
////    Serial.print(millis() - start_millis);
////    Serial.print("/t");
////    Serial.println(-1);
////    digitalWrite(led_pin, HIGH);
////    delay(50);
////    }
////
////   else if ((curr_left < left_threshold) && (left_touched)){
////    left_touched = false;
////    Serial.print(millis() - start_millis);
////    Serial.print("/t");
////    Serial.println(-2);
////    digitalWrite(led_pin, LOW);
////    }
////
////  else if ((curr_right > right_threshold) && !(right_touched)){
////    right_touched = true;
////    Serial.print(millis() - start_millis);
////    Serial.print("/t");
////    Serial.println(1);
////    digitalWrite(led_pin, HIGH);
////    delay(50);
////    }
////
////   else if ((curr_right < right_threshold) && (right_touched)){
////    right_touched = false;
////    Serial.print(millis() - start_millis);
////    Serial.print("/t");
////    Serial.println(2);
////    digitalWrite(led_pin, LOW);
////    }

}

void setup() {

  pinMode(led_pin, OUTPUT);
  pinMode(left_touch_pin, INPUT);
  pinMode(right_touch_pin, INPUT);

  //Lick arduino
  Serial.begin(115200);
  // Reward arduino
  Serial1.begin(115200);

   while (!Serial) { // needed to keep leonardo/micro from starting too fast!
   delay(10);
   }
   while (!Serial1) { // needed to keep leonardo/micro from starting too fast!
     delay(10);
   }

  Serial.setTimeout(5);
  base_licks = get_licks_baseline(base_licks);

  Serial1.print("20reward_left");
  delay(20);
  Serial1.print("20reward_right");



  // Starting session timer
  start_millis = millis();
}

void loop() {
  // see if there's incoming serial data:
  if (Serial.available() > 0) {

    // read and forward incoming string from serial buffer
    msg_int = int(Serial.parseInt());
    msg = Serial.readString();
    Serial1.print(msg_int+msg);

    if (msg=="reset"){
        // Call the modified get_licks_baseline function and store the returned struct in my_licks
        base_licks = get_licks_baseline(base_licks);
        // Serial.println("board_resetted");
    }

    // starting session clock
    else if (msg=="start_clock"){
        start_millis = millis();
        // Serial.println("clock_started");
    }

    // updating lick_threshold
    else if (msg=="update_lick_threshold_left"){
        // threshold_multiplier_left = msg_int;
        left_threshold = msg_int;
        // Serial.println("left_threshold_modified");
    }
    // updating lick_threshold
    else if (msg=="update_lick_threshold_right"){
        // threshold_multiplier_right = msg_int;
        right_threshold = msg_int;
        // Serial.println("right_threshold_modified");
    }

    // updating lick_threshold
    else if (msg=="update_lick_threshold"){
        left_threshold = msg_int;
        right_threshold = msg_int;
//         Serial.println("lick_threshold_modified");
    }
  }

 get_licks(base_licks, start_millis, left_threshold, right_threshold);




}
