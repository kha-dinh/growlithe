const { Firestore } = require('@google-cloud/firestore');

const firestore = new Firestore();

exports.handler = async (event, context) => {
    const body = event.body;
    const docId = event.docId;

    // Get collection and document reference
    const collection = firestore.collection('users');
    const docRef = collection.doc(docId);

    // Set document data from event
    await docRef.set({
        data: body,
        timestamp: Date.now()
    });

    // Update document with additional field
    await docRef.update({
        lastModified: Date.now()
    });

    const response = {
        statusCode: 200,
        body: JSON.stringify({ message: 'Document updated', docId: docId })
    };

    return response;
};
