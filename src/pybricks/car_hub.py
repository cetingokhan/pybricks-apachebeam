from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port,Button, Color
from pybricks.pupdevices import Remote
from pybricks.tools import wait, run_task
from uselect import poll
from usys import stdin, stdout
import ujson

hub = PrimeHub()

motor_back_right = Motor(Port.B)
motor_back_left = Motor(Port.F)
motor_front = Motor(Port.D)
eyes = UltrasonicSensor(Port.C)
motor_front.run_target(1000,0)
my_remote = Remote()

keyboard = poll()
keyboard.register(stdin)

pressed = ()
print("OK!")


def remote_button_pressed(buttons):
    if Button.LEFT_PLUS in buttons:
        motor_back_left.run_angle(1000,45, wait=False)
        motor_back_right.run_angle(1000,-45, wait=False)
    elif Button.LEFT_MINUS in buttons:
        motor_back_left.run_angle(1000,-45, wait=False)
        motor_back_right.run_angle(1000,45, wait=False)    
    
    if abs(motor_front.angle()) <= 15:
        if Button.RIGHT_MINUS in buttons:
            motor_front.run_angle(1000,5, wait=False)     
        elif Button.RIGHT_PLUS in buttons:
            motor_front.run_angle(1000,-5, wait=False) 

    if (Button.RIGHT_MINUS  not in buttons) & (Button.RIGHT_PLUS not in buttons):
        motor_front.run_target(1000,0, wait=False)
        
        
def main():
    eye_distance = 0
    stopped = False
    while True:    
        pressed = ()
        if not pressed:
            pressed = my_remote.buttons.pressed()
            if (len(pressed)==0) & motor_front.angle()!=0:            
                motor_front.run_target(1000,0,wait=False)       

        remote_button_pressed(pressed)
            
        current_distance = eyes.distance()
        if eye_distance != current_distance:
            eye_distance = current_distance
            try:
                if stopped:
                    if current_distance>300:
                        stopped = False
                else:
                    stdout.buffer.write(bytes(ujson.dumps({"distance":current_distance}),"UTF-8"))
            except:
                hub.light.on(Color.YELLOW * 0.3)

        if keyboard.poll(0):
            line = stdin.buffer.read(3)
            if line == b"red":
                hub.light.on(Color.RED)     
            elif line == b"blu":
                hub.light.on(Color.BLUE)
            elif line == b"grn":
                hub.light.on(Color.GREEN)
            elif line == b"off":
                hub.light.off()
            elif line == b"stp":
                hub.light.on(Color.RED)    
                #hub.speaker.beep()
                wait(10000)
                stopped = True
                hub.light.on(Color.GREEN)
        
        wait(0.1)

main()