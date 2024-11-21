particlesJS("particles-js", {
    "particles": {
        "number": {
            "value": 128,
            "density": {
                "enable": false,
                "value_area": 50
            }
        },
        "color": {
            "value": "#9166a9"
        },
        "shape": {
            "type": ["image", "img"],
            "image": {
                "src": "https://raw.githubusercontent.com/SteakTheStake/bonemeal-v2/28ee085435329e49783b3db641dcb03839c4a057/bonemeal/src/ui/img/spark.svg",
                "width": 1,
                "height": 1
            }
        },
        "opacity": {
            "value": 1,
            "random": true,
            "anim": {
                "enable": false,
                "speed": 1,
                "opacity_min": 0,
                "sync": false
            }
        },
        "size": {
            "value": 55,
            "random": true,
            "anim": {
                "enable": false,
                "speed": 21.55396073985969,
                "size_min": 26.34372979316184,
                "sync": false
            }
        },
        "line_linked": {
            "enable": false,
            "distance": 150,
            "color": "#ffffff",
            "opacity": 1,
            "width": 1
        },
        "move": {
            "enable": true,
            "speed": 18.919984233346483,
            "direction": "bottom-left",
            "random": false,
            "straight": false,
            "out_mode": "out",
            "bounce": false,
            "attract": {
                "enable": true,
                "rotateX": 2049.664958612536,
                "rotateY": 1891.9984233346484
            }
        }
    },
    "interactivity": {
        "detect_on": "window",
        "events": {
          "onhover": {
            "enable": true,
            "mode": "repulse"
          },
          "onclick": {
            "enable": false,
            "mode": "repulse"
          },
          "resize": true
        },
        "modes": {
          "grab": {
            "distance": 400,
            "line_linked": {
              "opacity": 0.5
            }
          },
          "bubble": {
            "distance": 400,
            "size": 4,
            "duration": 0.3,
            "opacity": 1,
            "speed": 3
          },
          "repulse": {
            "distance": 207.55665897642663,
            "duration": 0.4
          },
          "push": {
            "particles_nb": 4
          },
          "remove": {
            "particles_nb": 2
          }
        }
      },
      "retina_detect": true
  });