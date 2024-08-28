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

  // KWin 5 adds suffix to window title when there are multiple windows with the
  // same name, e.g. first window: "Hypertext", second window: "Hypertext <2>".
  // Remove the suffix as accessible name received from AT-SPI2 doesn't have it either
  //
  // For KWin 6, the suffix was dropped in
  // https://invent.kde.org/plasma/kwin/-/commit/aac5d562fbcfcea7124a71bbdf9ea647e6114f2d
  let caption = clients[i].caption;
  if (caption.match('^.* <[0-9]+>$'))
  {
    caption = (caption.substring(0, caption.lastIndexOf(' ')));
  }

  window_infos.push(
    {
      "caption": caption,
      "bufferGeometry.x": clients[i].bufferGeometry.x,
      "bufferGeometry.y": clients[i].bufferGeometry.y,
      "bufferGeometry.width": clients[i].bufferGeometry.width,
      "bufferGeometry.height": clients[i].bufferGeometry.height,
      "desktopFileName": clients[i].desktopFileName,
      "geometry.x": clients[i].bufferGeometry.x,
      "geometry.y": clients[i].bufferGeometry.y,
      "geometry.width": clients[i].bufferGeometry.width,
      "geometry.height": clients[i].bufferGeometry.height,
      "isOnCurrentWorkspace": isOnCurrentDesktop,
      "pid": clients[i].pid,
      "stackingOrder": clients[i].stackingOrder
    }
  );
}

const json_output = JSON.stringify(window_infos);
console.info(json_output)
