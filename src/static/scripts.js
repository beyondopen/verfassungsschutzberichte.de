if (!Array.prototype.filter) {
  Array.prototype.filter = function(func, thisArg) {
    "use strict";
    if (!((typeof func === "Function" || typeof func === "function") && this))
      throw new TypeError();

    var len = this.length >>> 0,
      res = new Array(len), // preallocate array
      t = this,
      c = 0,
      i = -1;
    if (thisArg === undefined) {
      while (++i !== len) {
        // checks to see if the key was set
        if (i in this) {
          if (func(t[i], i, t)) {
            res[c++] = t[i];
          }
        }
      }
    } else {
      while (++i !== len) {
        // checks to see if the key was set
        if (i in this) {
          if (func.call(thisArg, t[i], i, t)) {
            res[c++] = t[i];
          }
        }
      }
    }

    res.length = c; // shrink down array to proper size
    return res;
  };
}

// Production steps of ECMA-262, Edition 5, 15.4.4.19
// Reference: http://es5.github.io/#x15.4.4.19
if (!Array.prototype.map) {
  Array.prototype.map = function(callback /*, thisArg*/) {
    var T, A, k;

    if (this == null) {
      throw new TypeError("this is null or not defined");
    }

    // 1. Let O be the result of calling ToObject passing the |this|
    //    value as the argument.
    var O = Object(this);

    // 2. Let lenValue be the result of calling the Get internal
    //    method of O with the argument "length".
    // 3. Let len be ToUint32(lenValue).
    var len = O.length >>> 0;

    // 4. If IsCallable(callback) is false, throw a TypeError exception.
    // See: http://es5.github.com/#x9.11
    if (typeof callback !== "function") {
      throw new TypeError(callback + " is not a function");
    }

    // 5. If thisArg was supplied, let T be thisArg; else let T be undefined.
    if (arguments.length > 1) {
      T = arguments[1];
    }

    // 6. Let A be a new array created as if by the expression new Array(len)
    //    where Array is the standard built-in constructor with that name and
    //    len is the value of len.
    A = new Array(len);

    // 7. Let k be 0
    k = 0;

    // 8. Repeat, while k < len
    while (k < len) {
      var kValue, mappedValue;

      // a. Let Pk be ToString(k).
      //   This is implicit for LHS operands of the in operator
      // b. Let kPresent be the result of calling the HasProperty internal
      //    method of O with argument Pk.
      //   This step can be combined with c
      // c. If kPresent is true, then
      if (k in O) {
        // i. Let kValue be the result of calling the Get internal
        //    method of O with argument Pk.
        kValue = O[k];

        // ii. Let mappedValue be the result of calling the Call internal
        //     method of callback with T as the this value and argument
        //     list containing kValue, k, and O.
        mappedValue = callback.call(T, kValue, k, O);

        // iii. Call the DefineOwnProperty internal method of A with arguments
        // Pk, Property Descriptor
        // { Value: mappedValue,
        //   Writable: true,
        //   Enumerable: true,
        //   Configurable: true },
        // and false.

        // In browsers that support Object.defineProperty, use the following:
        // Object.defineProperty(A, k, {
        //   value: mappedValue,
        //   writable: true,
        //   enumerable: true,
        //   configurable: true
        // });

        // For best browser support, use the following:
        A[k] = mappedValue;
      }
      // d. Increase k by 1.
      k++;
    }

    // 9. return A
    return A;
  };
}

document.addEventListener("DOMContentLoaded", function() {
  // make sure the dummy text has at least an a4 ratio (sufficient in most cases)
  var imgs = document.getElementsByClassName("lazyload");
  for (var i = 0; i < imgs.length; i++) {
    var bla = imgs[i];
    bla.parentElement.style.minHeight =
      bla.parentElement.offsetWidth * 1.4142135624 + "px";
  }

  if (imgs.length && window.location.hash) {
    var element_to_scroll_to = document.getElementById(
      window.location.hash.substring(1)
    );

    element_to_scroll_to.scrollIntoView();
  }
});

// var colors = ["#cbd5e8", "#f4cae4", "#b3e2cd", "#fdcdac", "#e6f5c9"];

var colors = [
  "#a6cee3",
  "#1f78b4",
  "#b2df8a",
  "#33a02c",
  "#fb9a99",
  "#e31a1c",
  "#fdbf6f",
  "#ff7f00",
  "#cab2d6",
  "#6a3d9a",
  "#ffff99",
  "#b15928",
  "#8dd3c7",
  "#ffffb3",
  "#bebada",
  "#fb8072",
  "#80b1d3",
  "#fdb462",
  "#b3de69",
  "#fccde5",
  "#d9d9d9",
  "#bc80bd",
  "#ccebc5",
  "#ffed6f"
];

// http://colorbrewer2.org/#type=qualitative&scheme=Paired&n=12 + http://colorbrewer2.org/#type=qualitative&scheme=Set3&n=12

function drawLineChart(
  datas,
  seletion,
  height,
  yLabel,
  title,
  indexPage,
  searchPage
) {
  // no default params for old broswser
  if (height == null) height = 50;
  if (yLabel == null) yLabel = "Seiten";
  if (title == null) title = null;
  if (indexPage == null) indexPage = false;
  if (searchPage == null) searchPage = false;

  var ctx = document.createElement("canvas");
  ctx.id = "someId";
  ctx.height = height;
  ctx.style.height = height + "px";
  document.getElementById(seletion).appendChild(ctx);

  var minYear = 100000;
  var maxYear = 0;

  for (var di = 0; di < datas.length; di++) {
    var data = datas[di][1];
    for (var key in data) {
      // check if the property/key is defined in the object itself, not in parent
      if (data.hasOwnProperty(key)) {
        var y = parseInt(key);
        minYear = Math.min(minYear, y);
        maxYear = Math.max(maxYear, y);
      }
    }
  }

  var ds = [];
  // var max_num = 0;
  for (var di = 0; di < datas.length; di++) {
    // console.log(datas);
    var lab = datas[di][0];
    var data = datas[di][1];
    var years = [];

    var values = [];
    var cur_y = minYear;
    while (cur_y <= maxYear) {
      if (data.hasOwnProperty(cur_y)) {
        values.push(data[cur_y]);
      } else {
        values.push(0);
      }
      years.push(parseInt(cur_y));
      cur_y++;
    }

    // add dummy data when there is not enough data
    if (years.length === 1) {
      years.unshift(years[0] - 1);
      values.unshift(0);
      years.unshift(years[0] - 2);
      values.unshift(0);
    }

    if (years.length === 2 && years[1] - years[0] === 1) {
      years.unshift(years[0] - 1);
      values.unshift(0);
    }
    var color = null;
    if (di >= colors.length) {
      color = "#" + ((Math.random() * 0xffffff) << 0).toString(16); // random
    } else {
      color = colors[di];
    }

    ds.push({
      label: lab,
      lineTension: 0,
      fill: false,
      backgroundColor: color,
      borderColor: color,
      data: values,
      borderWidth: 2
    });

    // max_num += values.reduce((a, b) => a + b, 0);
  }
  // var hits = document.getElementById("hits");
  // if (hits != null) hits.innerText = max_num + " ";

  function done() {
    alert("haha");
    var url = myLine.toBase64Image();
    document.getElementById("url").src = url;
  }

  return [
    new Chart(ctx, {
      type: "line",
      data: {
        labels: years,
        datasets: ds
      },
      options: {
        tooltips: {
          callbacks: {
            label: function(tooltipItem, data) {
              var label = data.datasets[tooltipItem.datasetIndex].label || "";

              if (label) {
                label += ": ";
              }
              label += tooltipItem.yLabel.toFixed(6);
              return label;
            }
          }
        },
        responsive: true,
        maintainAspectRatio: false,
        title: {
          display: title !== null,
          text: title
        },
        legend: {
          display: searchPage !== true
        },
        scales: {
          xAxes: [
            {
              scaleLabel: {
                display: true,
                labelString: "Jahr"
              },
              ticks: {
                maxTicksLimit: indexPage ? 8 : 11
              }
            }
          ],
          yAxes: [
            {
              scaleLabel: {
                display: true,
                labelString: yLabel
              },
              ticks: {
                maxTicksLimit: height < 100 ? 5 : height < 400 ? 6 : 11,
                beginAtZero: true,
                integerSteps: true
              }
            }
          ]
        }
      }
    }),
    minYear,
    maxYear
  ];
}
