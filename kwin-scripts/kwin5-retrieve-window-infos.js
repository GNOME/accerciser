/*
 * @license: BSD
 *
 * All rights reserved. This program and the accompanying materials are made
 * available under the terms of the BSD which accompanies this distribution, and
 * is available at U{http://www.opensource.org/licenses/bsd-license.php}
 */

// JavaScript script to retrieve window information via KWin API

const currentDesktop = workspace.currentDesktop;

let window_infos = [];
const clients = workspace.clientList();
for (let i = 0; i < clients.length; i++) {
  const isOnCurrentDesktop = clients[i].onAllDesktops || clients[i].desktop == currentDesktop;
  window_infos.push(
    {
      "caption": clients[i].caption,
      "bufferGeometry.x": clients[i].bufferGeometry.x,
      "bufferGeometry.y": clients[i].bufferGeometry.y,
      "bufferGeometry.width": clients[i].bufferGeometry.width,
      "bufferGeometry.height": clients[i].bufferGeometry.height,
      "isOnCurrentWorkspace": isOnCurrentDesktop,
      "stackingOrder": clients[i].stackingOrder
    }
  );
}

const json_output = JSON.stringify(window_infos);
console.info(json_output)
