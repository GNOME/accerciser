/*
 * @license: BSD
 *
 * All rights reserved. This program and the accompanying materials are made
 * available under the terms of the BSD which accompanies this distribution, and
 * is available at U{http://www.opensource.org/licenses/bsd-license.php}
 */

// JavaScript script to retrieve window information via KWin API

// build a JSON array containing one object for each window
let window_infos = [];
const clients = workspace.windowList();
for (let i = 0; i < clients.length; i++) {
  window_infos.push(
    {
      "caption": clients[i].caption,
      "bufferGeometry.x": clients[i].bufferGeometry.x,
      "bufferGeometry.y": clients[i].bufferGeometry.y,
      "bufferGeometry.width": clients[i].bufferGeometry.width,
      "bufferGeometry.height": clients[i].bufferGeometry.height,
      "stackingOrder": clients[i].stackingOrder
    }
  );
}

const json_output = JSON.stringify(window_infos);
print(json_output)
