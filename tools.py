from routines import *
from objects import GoslingAgent
#This file is for strategic tools

def find_hits(agent,targets):
    #find_hits takes a dict of (left,right) target pairs and finds routines that could hit the ball between those target pairs
    #find_hits is only meant for routines that require a defined intercept time/place in the future
    #find_hits should not be called more than once in a given tick, as it has the potential to use an entire tick to calculate

    #Example Useage:
    #targets = {"goal":(opponent_left_post,opponent_right_post), "anywhere_but_my_net":(my_right_post,my_left_post)}
    #hits = find_hits(agent,targets)
    #print(hits)
    #>{"goal":[a ton of jump and aerial routines,in order from soonest to latest], "anywhere_but_my_net":[more routines and stuff]}


    # agent:GoslingAgent = agent # Debug
    hits = {name:[] for name in targets}
    struct = agent.ball_prediction
    #Begin looking at slices 0.25s into the future
    #The number of slices 
    i = 15
    while i < len(struct.slices):
        #Gather some data about the slice
        intercept_time = struct.slices[i].game_seconds
        time_remaining = intercept_time - agent.time
        if time_remaining > 0:
            ball_location = Vector3(struct.slices[i].physics.location)
            ball_velocity = Vector3(struct.slices[i].physics.velocity).magnitude()

            if abs(ball_location[1]) > 5250:
                break #abandon search if ball is scored at/after this point
        
            #determine the next slice we will look at, based on ball velocity (slower ball needs fewer slices)
            i += 15 - cap(int(ball_velocity//150),0,13)
            
            car_to_ball = ball_location - agent.me.location
            #Adding a True to a vector's normalize will have it also return the magnitude of the vector
            direction, distance = car_to_ball.normalize(True)


            #How far the car must turn in order to face the ball, for forward and reverse
            forward_angle = direction.angle(agent.me.forward)
            backward_angle = math.pi - forward_angle

            #Accounting for the average time it takes to turn and face the ball
            #Backward is slightly longer as typically the car is moving forward and takes time to slow down
            forward_time = time_remaining - (forward_angle * 0.318)
            backward_time = time_remaining - (backward_angle * 0.418)

            #If the car only had to drive in a straight line, we ensure it has enough time to reach the ball (a few assumptions are made)
            forward_flag = forward_time > 0.0 and (distance*1.025 / forward_time) < (2300 if agent.me.boost > 30 else max(1410, agent.me.velocity.flatten().magnitude()))
            backward_flag = distance < 1500 and backward_time > 0.0 and (distance*1.05 / backward_time) < 1200
            
            #Provided everything checks out, we begin to look at the target pairs
            if forward_flag or backward_flag:
                for pair in targets:
                    #First we correct the target coordinates to account for the ball's radius
                    #If fits == True, the ball can be scored between the target coordinates
                    left, right, fits = post_correction(ball_location, targets[pair][0], targets[pair][1])
                    if fits:
                        #Now we find the easiest direction to hit the ball in order to land it between the target points
                        left_vector = (left - ball_location).normalize()
                        right_vector = (right - ball_location).normalize()
                        best_shot_vector = direction.clamp(left_vector, right_vector)

                        #The slope represents how close the car is to the chosen vector, higher = better
                        slope = best_shot_vector.flatten().normalize().dot(car_to_ball.flatten().normalize()) * 0.5
                        slope += distance * 0.0001 # the farther away we are, the easier it is to fix a bad slope

                        if not in_field(ball_location - best_shot_vector * 200, 1):
                            # we don't want to try and hit the ball when it puts us against the wall
                            continue

                        if forward_flag:
                            if ball_location[2] <= 300 and slope > 0.35:
                                hits[pair].append(jump_shot(ball_location, intercept_time, best_shot_vector, slope))
                            elif slope > 0.7 and cap(ball_location[2]-400, 100, 2000) * 0.1 < agent.me.boost:
                                # if abs((car_to_ball / forward_time) - agent.me.velocity).magnitude() - 300 < 400 * forward_time:
                                hits[pair].append(aerial_shot(ball_location, intercept_time, best_shot_vector, slope))
                        elif backward_flag and ball_location[2] < 300 and slope > 0.5:
                            hits[pair].append(jump_shot(ball_location, intercept_time, best_shot_vector, slope, -1))
        else:
            i += 1
    return hits